# run_celery.py
# Script to start Celery worker

import os
from celery_config import celery_app

if __name__ == '__main__':
    # This will start the worker with the task imported from celery_config
    celery_app.worker_main(['worker', '--loglevel=INFO', '-E'])