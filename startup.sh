#!/bin/bash
# Azure App Service startup script for FastAPI
# App Service ends any request at 230 seconds, so workers give up just before that.
gunicorn -w ${WEB_CONCURRENCY:-2} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000} --timeout 220
