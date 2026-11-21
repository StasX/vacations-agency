from io import BytesIO
from os import environ
from pathlib import Path
from uuid import uuid4
import warnings

from flask import abort, current_app, send_file
from PIL import Image, UnidentifiedImageError
from werkzeug.http import parse_date


class ImageHandler:
    __image_path = "static/images/vacations"
    __no_image_path = "static/images/no_photo.jpg"
    max_bytes = 5 * 1024 * 1024
    max_pixels = 20_000_000
    formats = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}

    @staticmethod
    def _directory():
        return Path(current_app.root_path) / ImageHandler.__image_path

    @staticmethod
    def _validate_name(image_name):
        if not image_name or image_name in {".", ".."} or Path(image_name).name != image_name or any(
            separator in image_name for separator in ("/", "\\", "\0")
        ):
            abort(400, description="Invalid image filename.")

    @staticmethod
    def _path(image_name):
        ImageHandler._validate_name(image_name)
        directory = ImageHandler._directory().resolve()
        target = (directory / image_name).resolve()
        if target.parent != directory:
            abort(400, description="Invalid image filename.")
        return target

    @staticmethod
    def save_image(image, *, before_write=None):
        if image is None or not image.filename:
            return None
        contents = image.stream.read(ImageHandler.max_bytes + 1)
        if len(contents) > ImageHandler.max_bytes:
            abort(413, description="Images must be no larger than 5 MB.")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(BytesIO(contents)) as candidate:
                    image_format = candidate.format
                    if image_format not in ImageHandler.formats:
                        abort(400, description="Upload a JPEG, PNG, or WebP image.")
                    if candidate.width * candidate.height > ImageHandler.max_pixels:
                        abort(400, description="Image dimensions are too large.")
                    candidate.verify()
                with Image.open(BytesIO(contents)) as candidate:
                    candidate.load()
                    clean_image = candidate.copy()
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombWarning, Image.DecompressionBombError):
            abort(400, description="The uploaded file is not a valid image.")
        # Choose the extension from decoded content and strip embedded metadata.
        clean_image.info.clear()
        image_name = str(uuid4()) + ImageHandler.formats[image_format]
        try:
            if before_write is not None:
                before_write(image_name)
            if environ.get("MINIO_ENDPOINT"):
                from utils.minio_images import image_storage

                with BytesIO() as contents:
                    clean_image.save(contents, format=image_format)
                    length = contents.tell()
                    contents.seek(0)
                    client, bucket = image_storage()
                    client.put_object(bucket, image_name, contents, length, content_type=Image.MIME[image_format])
            else:
                directory = ImageHandler._directory()
                directory.mkdir(parents=True, exist_ok=True)
                target = ImageHandler._path(image_name)
                try:
                    clean_image.save(target, format=image_format)
                except Exception:
                    target.unlink(missing_ok=True)
                    raise
        finally:
            clean_image.close()
        return image_name

    @staticmethod
    def update_image(old_image_name, image):
        if image is None or not image.filename:
            return old_image_name
        image_name = ImageHandler.save_image(image)
        ImageHandler.delete_image(old_image_name)
        return image_name

    @staticmethod
    def delete_image(image_name):
        if not image_name:
            return
        if environ.get("MINIO_ENDPOINT"):
            from utils.minio_images import image_storage

            ImageHandler._validate_name(image_name)
            client, bucket = image_storage()
            client.remove_object(bucket, image_name)
            return
        ImageHandler._path(image_name).unlink(missing_ok=True)

    @staticmethod
    def send_image(image_name):
        if not environ.get("MINIO_ENDPOINT"):
            return send_file(ImageHandler.get_image_path(image_name))

        from minio.error import S3Error
        from utils.minio_images import image_storage

        ImageHandler._validate_name(image_name)
        client, bucket = image_storage()
        try:
            response = client.get_object(bucket, image_name)
        except S3Error as error:
            if error.code != "NoSuchKey":
                raise
            return send_file(Path(current_app.root_path) / ImageHandler.__no_image_path)

        try:
            return send_file(
                BytesIO(response.read()),
                download_name=image_name,
                etag=response.headers.get("ETag", "").strip('"') or False,
                last_modified=parse_date(response.headers.get("Last-Modified")),
            )
        finally:
            response.close()
            response.release_conn()

    @staticmethod
    def get_image_path(image_name):
        image_path = ImageHandler._path(image_name)
        if not image_path.is_file():
            image_path = Path(current_app.root_path) / ImageHandler.__no_image_path
        return image_path
