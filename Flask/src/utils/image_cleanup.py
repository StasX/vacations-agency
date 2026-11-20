"""Process image deletions recorded by committed vacation changes."""
import logging
from time import sleep

from utils.dal import DAL
from utils.image_handler import ImageHandler


logger = logging.getLogger(__name__)


def enqueue_image_cleanup(dal, image_name):
    if image_name:
        dal.insert(
            "INSERT INTO vacation_image_cleanup (image_name) VALUES (%s) "
            "ON DUPLICATE KEY UPDATE next_attempt_at = CURRENT_TIMESTAMP",
            (image_name,),
        )


def process_next_image(dal):
    # Avoid gap locks that could block unrelated enqueues during a storage call.
    with dal.transaction(isolation_level="READ COMMITTED"):
        pending = dal.get_scalar(
            "SELECT image_name FROM vacation_image_cleanup "
            "WHERE next_attempt_at <= CURRENT_TIMESTAMP "
            "ORDER BY next_attempt_at, image_name LIMIT 1 FOR UPDATE SKIP LOCKED"
        )
        if pending is None:
            return False

        image_name = pending["image_name"]
        # Uploads get unique names. Removing any remaining reference will enqueue
        # the same name again under this queue key.
        referenced = dal.get_scalar(
            "SELECT id FROM vacations WHERE CAST(image AS BINARY) = CAST(%s AS BINARY) LIMIT 1",
            (image_name,),
        )
        if referenced is None:
            try:
                ImageHandler.delete_image(image_name)
            except Exception:
                logger.exception("Failed to remove vacation image %r; retrying", image_name)
                dal.update(
                    "UPDATE vacation_image_cleanup "
                    "SET next_attempt_at = CURRENT_TIMESTAMP + INTERVAL 1 MINUTE WHERE image_name = %s",
                    (image_name,),
                )
                return True

        dal.delete("DELETE FROM vacation_image_cleanup WHERE image_name = %s", (image_name,))
        return True


def run_worker():
    from app import app

    while True:
        try:
            with app.app_context():
                dal = DAL()
                try:
                    for _ in range(100):
                        if not process_next_image(dal):
                            break
                    else:
                        continue
                finally:
                    dal.close()
        except Exception:
            logger.exception("Vacation image cleanup could not process the queue")
        sleep(5)


if __name__ == "__main__":
    run_worker()
