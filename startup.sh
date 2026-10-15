#!/bin/bash
# Azure App Service startup script for FastAPI
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT:-8000} --timeout 600
