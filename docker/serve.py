"""
SageMaker custom inference server.
Responds to GET /ping (health check) and POST /invocations (prediction).
SageMaker starts the container with this script and expects port 8080.
"""

import os
import json
import logging
import joblib
import pandas as pd
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
model = None

MODEL_PATH = os.environ.get("MODEL_PATH", "/opt/ml/model/credit_score_model.pkl")


def load_model():
    global model
    logger.info(f"Loading model from {MODEL_PATH}")
    model = joblib.load(MODEL_PATH)
    logger.info("Model loaded successfully")


@app.route("/ping", methods=["GET"])
def ping():
    """SageMaker health check endpoint."""
    status = 200 if model is not None else 404
    return Response(
        response=json.dumps({"status": "healthy" if model else "not ready"}),
        status=status,
        mimetype="application/json",
    )


@app.route("/invocations", methods=["POST"])
def invocations():
    """SageMaker inference endpoint."""
    if request.content_type != "application/json":
        return Response(response="Unsupported media type", status=415)

    try:
        data = json.loads(request.data.decode("utf-8"))
        df = pd.DataFrame([data])
        prediction = model.predict(df)[0]

        return Response(
            response=json.dumps({"credit_score": str(prediction)}),
            status=200,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return Response(
            response=json.dumps({"error": str(e)}),
            status=500,
            mimetype="application/json",
        )


if __name__ == "__main__":
    load_model()
    app.run(host="0.0.0.0", port=8080)
