import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("GUNICORN_WORKERS", 2))
worker_class = "gthread"
threads = int(os.environ.get("GUNICORN_THREADS", 4))
timeout = 600
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
