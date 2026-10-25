from io import BytesIO
from pathlib import Path
from uuid import uuid4
import warnings

from flask import abort, current_app
from PIL import Image, UnidentifiedImageError


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
    def _path(image_name):
        directory = ImageHandler._directory().resolve()
        if not image_name or Path(image_name).name != image_name or "\\" in image_name:
            abort(400, description="Invalid image filename.")
        target = (directory / image_name).resolve()
        if target.parent != directory:
            abort(400, description="Invalid image filename.")
        return target

    @staticmethod
    def save_image(image):
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
        if image_name:
            ImageHandler._path(image_name).unlink(missing_ok=True)

    @staticmethod
    def get_image_path(image_name):
        image_path = ImageHandler._path(image_name)
        if not image_path.is_file():
            image_path = Path(current_app.root_path) / ImageHandler.__no_image_path
        return image_path
