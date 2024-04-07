import multiprocessing
import os


accesslog = "-"
bind = ["0.0.0.0:8000"]
capture_output = True
forwarded_allow_ips = "*"
preload_app = True
reuse_port = True
workers = int(os.environ.get("NUM_GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
wsgi_app = "calls.wsgi"


def post_worker_init(worker):
    from faker import Faker

    Faker.seed()  # Faker needs to be re-seeded before use (preload_app = True)
