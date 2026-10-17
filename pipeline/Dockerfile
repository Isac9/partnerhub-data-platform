FROM python:3.12-slim
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
ENV PYTHONPATH=/app/pipeline PYTHONUNBUFFERED=1
WORKDIR /app
CMD ["python", "-m", "partnerhub.run_all"]
