from functools import lru_cache
from io import BytesIO
from mimetypes import guess_type
from os import environ
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager, Timeout


@lru_cache(maxsize=1)
def image_storage():
    client = Minio(
        environ["MINIO_ENDPOINT"],
        access_key=environ["MINIO_ACCESS_KEY"],
        secret_key=environ["MINIO_SECRET_KEY"],
        secure=environ.get("MINIO_SECURE", "true").lower() == "true",
        http_client=PoolManager(timeout=Timeout(connect=3, read=20), retries=False),
    )
    return client, environ.get("MINIO_BUCKET", "vacation-images")


def object_exists(client, bucket, name):
    try:
        client.stat_object(bucket, name)
    except S3Error as error:
        if error.code == "NoSuchKey":
            return False
        raise
    return True


def initialize():
    client, bucket = image_storage()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    marker = "_migration/initial-images"
    if object_exists(client, bucket, marker):
        return

    bundled = Path(__file__).resolve().parents[1] / "static/images/vacations"
    for directory in (Path("/legacy-vacation-images"), bundled):
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            content_type, _ = guess_type(path.name)
            if content_type not in {"image/jpeg", "image/png", "image/webp"}:
                continue
            if path.is_file() and not path.is_symlink() and not object_exists(client, bucket, path.name):
                client.fput_object(bucket, path.name, str(path), content_type=content_type)

    client.put_object(bucket, marker, BytesIO(), 0)


if __name__ == "__main__":
    initialize()
