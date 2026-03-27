"""
SageMaker custom inference server.
Responds to GET /ping (health check) and POST /invocations (prediction).

Dataset : Lending Club (141k rows)
Model   : sklearn Pipeline (StandardScaler → LogisticRegression, AUC 0.702)
Target  : Binary — 0 = No Default, 1 = Default

The model is a full Pipeline — it handles its own scaling.
serve.py only needs to align column order before passing to predict_proba.
"""

import os
import json
import logging
import threading
import joblib
import numpy as np
import pandas as pd
from flask import Flask, request, Response

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

MODEL_PATH = os.environ.get("MODEL_PATH", "/opt/ml/model/credit_scoring_model.pkl")

# Feature order must match exactly what the model was trained on
FEATURES = [
    "loan_amnt", "term", "int_rate", "installment", "grade", "sub_grade",
    "emp_length", "home_ownership", "annual_inc", "verification_status",
    "purpose", "dti", "delinq_2yrs", "inq_last_6mths", "open_acc",
    "pub_rec", "revol_bal", "revol_util", "total_acc",
]

DEFAULT_LABELS = {0: "No Default", 1: "Default"}

# Calibrated threshold — model trained with class_weight="balanced"
# on a 19.8% default rate. 0.40 gives realistic variation.
THRESHOLD = 0.40

model            = None
model_load_error = None


def _load_model():
    global model, model_load_error
    try:
        logger.info(f"Loading model from {MODEL_PATH}")
        model = joblib.load(MODEL_PATH)
        logger.info(f"Model loaded: {type(model).__name__}")
    except Exception as exc:
        model_load_error = str(exc)
        logger.error(f"Failed to load model: {exc}")


threading.Thread(target=_load_model, daemon=True).start()


def preprocess(raw: dict) -> pd.DataFrame:
    """
    Build a single-row DataFrame aligned to the training feature order.
    The Pipeline handles StandardScaler internally — no separate scaling here.
    """
    df = pd.DataFrame([raw])
    df = df.reindex(columns=FEATURES, fill_value=0)
    logger.info(f"Input features: {df.iloc[0].to_dict()}")
    return df


@app.route("/ping", methods=["GET"])
def ping():
    if model_load_error:
        return Response(
            json.dumps({"status": "error", "detail": model_load_error}),
            status=500, mimetype="application/json"
        )
    if model is None:
        return Response(
            json.dumps({"status": "loading"}),
            status=503, mimetype="application/json"
        )
    return Response(
        json.dumps({"status": "healthy"}),
        status=200, mimetype="application/json"
    )


@app.route("/invocations", methods=["POST"])
def invocations():
    if model is None:
        return Response(
            json.dumps({"error": "Model not ready"}),
            status=503, mimetype="application/json"
        )
    if request.content_type != "application/json":
        return Response("Unsupported media type", status=415)

    try:
        raw      = json.loads(request.data.decode("utf-8"))
        features = preprocess(raw)

        prob = float(model.predict_proba(features)[0][1])
        pred = int(prob >= THRESHOLD)
        label = DEFAULT_LABELS.get(pred, str(pred))

        logger.info(f"prob={prob:.4f}  pred={pred}  label={label}")

        return Response(
            json.dumps({
                "prediction":         pred,
                "label":              label,
                "default_probability": round(prob, 4),
            }),
            status=200, mimetype="application/json"
        )

    except Exception as exc:
        logger.error(f"Prediction error: {exc}", exc_info=True)
        return Response(
            json.dumps({"error": str(exc)}),
            status=500, mimetype="application/json"
        )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
