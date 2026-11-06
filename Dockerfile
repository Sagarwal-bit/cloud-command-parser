# Inference service image. No model weights inside: they are downloaded from object storage at start-up.
FROM python:3.11.9-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY service/requirements.txt service/requirements.txt
RUN pip install -r service/requirements.txt
COPY service/ service/
COPY data/schema.json data/schema.json
EXPOSE 8000
CMD ["uvicorn", "service.app:app", "--host", "0.0.0.0", "--port", "8000"]
