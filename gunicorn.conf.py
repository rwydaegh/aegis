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


def post_fork(server, worker):
    """Warm the dosimetry numba kernels off the first real request.

    The first lab/viewer compute on a fresh worker otherwise pays ~60 s of numba
    JIT. We compile in a background daemon thread (so /api/health stays green and
    the worker is routable immediately); on the real host CPU (so cached object
    code is valid); with NUMBA_CACHE_DIR on a persistent volume the second boot
    onward is a fast cache load. Best-effort and disableable via AEGIS_WARMUP=0.
    """
    if os.environ.get("AEGIS_WARMUP", "1") == "0":
        return
    try:
        from aegis.viewer.warmup import warm_kernels_async

        warm_kernels_async()
    except Exception as exc:  # never let warm-up break worker boot
        worker.log.warning("kernel warm-up not started: %s", exc)
