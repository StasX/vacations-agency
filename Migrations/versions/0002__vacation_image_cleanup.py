"""Create the InnoDB image cleanup queue without modifying vacation rows.

Reapplying preserves queued work. The table can stay if application code is
rolled back.
"""


def upgrade(connection):
    cursor = connection.cursor()
    try:
        cursor.execute("SHOW TABLES LIKE 'vacations'")
        if cursor.fetchone() is None:
            raise RuntimeError("Expected the existing vacations table before adding image cleanup")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vacation_image_cleanup (
                image_name VARCHAR(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_bin NOT NULL,
                next_attempt_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (image_name),
                KEY image_cleanup_due (next_attempt_at, image_name)
            ) ENGINE=InnoDB
        """)
    finally:
        cursor.close()
