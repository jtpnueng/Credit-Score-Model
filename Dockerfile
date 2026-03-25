# Root Dockerfile — alias for the SageMaker custom inference container.
# See docker/Dockerfile.sagemaker for the full source.
FROM python:3.9-slim

RUN pip install --no-cache-dir \
    scikit-learn==1.2.2 \
    "numpy<2.0" \
    pandas \
    joblib \
    flask \
    gunicorn

RUN mkdir -p /opt/ml/model /opt/program

COPY Models/credit_scoring_model.pkl /opt/ml/model/credit_score_model.pkl
COPY docker/serve.py /opt/program/serve.py

ENV PYTHONUNBUFFERED=TRUE
ENV MODEL_PATH=/opt/ml/model/credit_score_model.pkl
ENV PATH="/opt/program:${PATH}"

WORKDIR /opt/program

EXPOSE 8080

ENTRYPOINT ["python", "serve.py"]
