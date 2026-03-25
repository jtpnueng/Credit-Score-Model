from fastapi import FastAPI, HTTPException
import boto3
import json
import os

app = FastAPI(title="Credit Score API")

ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "credit-score-endpoint")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

client = boto3.client("sagemaker-runtime", region_name=AWS_REGION)


@app.get("/health")
async def health():
    return {"status": "healthy", "endpoint": ENDPOINT_NAME}


@app.post("/predict")
async def predict(data: dict):
    # Field names must match the training CSV columns exactly
    payload = {
        "Age": data.get("age"),
        "Gender": data.get("gender"),
        "Income": data.get("income"),
        "Education": data.get("education"),
        "Marital Status": data.get("marital_status"),
        "Number of Children": data.get("num_children"),
        "Home Ownership": data.get("home_ownership"),
    }

    try:
        response = client.invoke_endpoint(
            EndpointName=ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(payload),
        )
        return json.loads(response["Body"].read().decode())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
