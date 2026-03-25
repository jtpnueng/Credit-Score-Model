"""
SageMaker custom inference server.
Responds to GET /ping (health check) and POST /invocations (prediction).
SageMaker starts the container with this script and expects port 8080.

Design decisions:
- Model is loaded in a background thread so Flask starts immediately.
  SageMaker calls /ping repeatedly; it returns 200 only once the model is
  ready, and 503 while it is still loading.  This prevents a crash-loop if
  the load takes a few seconds.
- All errors are caught and returned as JSON — the container never exits
  unexpectedly, which would cause SageMaker to mark the endpoint as Failed.
"""

import os
import json
import logging
import threading
import joblib
import pandas as pd
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "/opt/ml/model/credit_scoring_model.pkl")
SCALER_PATH = os.environ.get("SCALER_PATH", "/opt/ml/model/scaler.pkl")

model = None
scaler = None
model_load_error = None   # set if loading fails — surfaced in /ping


# ---------------------------------------------------------------------------
# Background model loader — Flask starts immediately, model loads in parallel
# ---------------------------------------------------------------------------
def _load_model():
    global model, scaler, model_load_error
    try:
        logger.info(f"Loading model from {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        logger.info("Model loaded successfully")

        if os.path.exists(SCALER_PATH):
            logger.info(f"Loading scaler from {SCALER_PATH}")
            scaler = joblib.load(SCALER_PATH)
            logger.info("Scaler loaded successfully")
        else:
            logger.info("No separate scaler found — assuming pipeline handles scaling")

    except Exception as exc:
        model_load_error = str(exc)
        logger.error(f"Failed to load model: {exc}")


threading.Thread(target=_load_model, daemon=True).start()


# ---------------------------------------------------------------------------
# SageMaker required endpoints
# ---------------------------------------------------------------------------
@app.route("/ping", methods=["GET"])
def ping():
    """
    SageMaker calls this repeatedly after container start.
    Return 200 only when the model is ready; 503 while loading; 500 on error.
    """
    if model_load_error:
        body = {"status": "error", "detail": model_load_error}
        return Response(response=json.dumps(body), status=500, mimetype="application/json")

    if model is None:
        body = {"status": "loading"}
        return Response(response=json.dumps(body), status=503, mimetype="application/json")

    return Response(
        response=json.dumps({"status": "healthy"}),
        status=200,
        mimetype="application/json",
    )


@app.route("/invocations", methods=["POST"])
def invocations():
    """SageMaker inference endpoint — accepts JSON, returns prediction."""
    if model is None:
        return Response(
            response=json.dumps({"error": "Model not ready"}),
            status=503,
            mimetype="application/json",
        )

    if request.content_type != "application/json":
        return Response(response="Unsupported media type", status=415)

    try:
        data = json.loads(request.data.decode("utf-8"))
        df = pd.DataFrame([data])

        # Apply scaler only if it was loaded separately (i.e. not part of pipeline)
        if scaler is not None:
            numeric_cols = df.select_dtypes(include="number").columns
            df[numeric_cols] = scaler.transform(df[numeric_cols])

        prediction = model.predict(df)[0]

        return Response(
            response=json.dumps({"credit_score": str(prediction)}),
            status=200,
            mimetype="application/json",
        )
    except Exception as exc:
        logger.error(f"Prediction error: {exc}")
        return Response(
            response=json.dumps({"error": str(exc)}),
            status=500,
            mimetype="application/json",
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
