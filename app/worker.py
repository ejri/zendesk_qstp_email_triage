import json
import logging
import time
from .config import REDIS_URL, LOG_LEVEL
from .db import init_db
from .main import process_ticket

import redis

logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)


def main():
    init_db()
    if not REDIS_URL:
        logger.warning("REDIS_URL not set; worker will not poll a queue.")
        while True:
            time.sleep(60)
        return

    r = redis.from_url(REDIS_URL)
    logger.info("Worker started, polling triage_queue")

    while True:
        item = r.brpop("triage_queue", timeout=5)
        if not item:
            continue
        _, data = item
        try:
            payload = json.loads(data)
            ticket_id = payload["ticket_id"]
            process_ticket(ticket_id)
        except Exception as e:
            logger.exception(f"Error processing queued job: {e}")


if __name__ == "__main__":
    main()