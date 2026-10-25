from io import BytesIO

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from conftest import make_image
from logic.vacations_logic import VacationsLogic
from models.vacation_model import VacationModel
from utils.image_handler import ImageHandler


def upload(contents, filename="trip.jpg"):
    return FileStorage(stream=BytesIO(contents), filename=filename)


@pytest.mark.parametrize("contents", [b"<script>alert(1)</script>", b"\xff\xd8broken", b""])
def test_fake_or_corrupt_images_rejected(app, image_directory, contents):
    with app.app_context(), pytest.raises(BadRequest):
        ImageHandler.save_image(upload(contents))
    assert not list(image_directory.iterdir())


@pytest.mark.parametrize("image_format,suffix", [("JPEG", ".jpg"), ("PNG", ".png"), ("WEBP", ".webp")])
def test_decoded_content_controls_extension(app, image_directory, image_format, suffix):
    with app.app_context():
        name = ImageHandler.save_image(upload(make_image(image_format=image_format), "../../attack.html"))
    assert name.endswith(suffix)
    with Image.open(image_directory / name) as saved:
        assert saved.format == image_format
        saved.verify()


def test_trailing_payload_removed(app, image_directory):
    with app.app_context():
        name = ImageHandler.save_image(upload(make_image() + b"<script>malicious</script>"))
    assert b"<script>" not in (image_directory / name).read_bytes()


def test_oversized_image_rejected(app, image_directory, monkeypatch):
    monkeypatch.setattr(ImageHandler, "max_bytes", 10)
    with app.app_context(), pytest.raises(RequestEntityTooLarge):
        ImageHandler.save_image(upload(make_image()))
    assert not list(image_directory.iterdir())


def test_excessive_pixels_rejected(app, image_directory, monkeypatch):
    monkeypatch.setattr(ImageHandler, "max_pixels", 1)
    with app.app_context(), pytest.raises(BadRequest):
        ImageHandler.save_image(upload(make_image()))
    assert not list(image_directory.iterdir())


@pytest.mark.parametrize("name", ["../outside.jpg", "..\\outside.jpg", "/outside.jpg"])
def test_image_paths_cannot_escape_storage(app, name):
    with app.app_context():
        with pytest.raises(BadRequest):
            ImageHandler.get_image_path(name)
        with pytest.raises(BadRequest):
            ImageHandler.delete_image(name)


@pytest.mark.parametrize("operation", ["insert", "update", "delete"])
def test_database_failure_preserves_old_image_and_cleans_new(app, image_directory, operation):
    old = image_directory / "old.jpg"
    old.write_bytes(make_image())
    app.test_dal.get_scalar.return_value = {"image": "old.jpg"}
    getattr(app.test_dal, operation).side_effect = RuntimeError("database unavailable")
    vacation = VacationModel(12, "1", "Trip", "2099-01-01", "2099-01-02", "100", upload(make_image("blue")))
    with app.app_context(), pytest.raises(RuntimeError):
        logic = VacationsLogic()
        if operation == "insert":
            logic.add_vacation(vacation)
        elif operation == "update":
            logic.update_vacation(vacation)
        else:
            logic.delete_vacation(12)
    assert list(image_directory.iterdir()) == [old]
    assert old.read_bytes() == make_image()


def test_request_limit_returns_413_page(client, app):
    app.config["MAX_CONTENT_LENGTH"] = 100
    app.config["CSRF_ENABLED"] = True
    response = client.post("/vacations/add", data={"image": (BytesIO(b"x" * 200), "large.jpg")})
    assert response.status_code == 413
    assert b'class="error-page"' in response.data
