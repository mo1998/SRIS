"""RQ worker entrypoint for durable evaluation jobs."""

import os

import redis
from rq import Connection, Worker

from app.config import settings


def main() -> None:
    redis_connection = redis.from_url(settings.REDIS_URL)
    queue_name = os.getenv("EVALUATION_QUEUE_NAME", settings.EVALUATION_QUEUE_NAME)
    with Connection(redis_connection):
        worker = Worker([queue_name])
        worker.work()


if __name__ == "__main__":
    main()