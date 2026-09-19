FROM python:3.12-slim

WORKDIR /app

# deps first for layer caching.
# --trusted-host lets the build succeed behind corporate proxies that inject a
# self-signed cert into the TLS chain (harmless on normal networks).
COPY requirements.txt .
RUN pip install --no-cache-dir \
    --trusted-host pypi.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

# app code (data + ground truth come in as mounts, not baked into the image)
COPY scoring.py app.py score_cli.py ./

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
