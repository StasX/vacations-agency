from datetime import date, datetime
from hashlib import sha512
from io import BytesIO

import pytest
from werkzeug.datastructures import FileStorage

from utils.date_handler import DateHandler
from utils.image_handler import ImageHandler
from utils.logger import Logger
from utils.security import Security
from utils.app_config import AppConfig


def upload(name="photo.jpg", contents=b"image"):
    return FileStorage(stream=BytesIO(contents), filename=name)


def test_dates():
    assert DateHandler.format_date(date(2028, 2, 29)) == "29/02/2028"
    assert DateHandler.to_date("2028-02-29") == datetime(2028, 2, 29)
    before = datetime.now()
    assert before <= DateHandler.now() <= datetime.now()
    value = {"start_date": date(2028, 2, 29), "end_date": date(2028, 3, 1), "id": 1}
    assert DateHandler.format_vacation_dates(value) == {
        "start_date": "29/02/2028", "end_date": "01/03/2028", "id": 1,
    }


@pytest.mark.parametrize("value", ["bad", "2027-02-29", "2028-13-01", ""])
def test_invalid_date_conversion(value):
    with pytest.raises(ValueError):
        DateHandler.to_date(value)


def test_security_hash_uses_salt_and_utf8(monkeypatch):
    monkeypatch.setattr(AppConfig, "passwords_salt", "test-salt")
    assert Security.hash("pässword") == sha512("pässwordtest-salt".encode()).hexdigest()
    assert Security.hash("other") != Security.hash("pässword")
    first = Security.hash("pässword")
    monkeypatch.setattr(AppConfig, "passwords_salt", "other-salt")
    assert Security.hash("pässword") != first


def test_logger_appends_timestamp_and_exception(tmp_path, monkeypatch):
    path = tmp_path / "crashes.log"
    monkeypatch.setattr(Logger, "_Logger__path", str(path))
    monkeypatch.setattr(DateHandler, "now", lambda: datetime(2028, 1, 1))
    Logger.write_log(ValueError("first"))
    Logger.write_log("second")
    content = path.read_text()
    assert content.count("2028-01-01 00:00:00") == 2
    assert "first\n" in content and "second\n" in content


def test_save_image_unique_names_and_safe_basename(app, image_directory):
    with app.app_context():
        first = ImageHandler.save_image(upload("../../photo.jpg"))
        second = ImageHandler.save_image(upload("photo.jpg"))
    assert first != second
    assert "/" not in first and "\\" not in first
    assert first.endswith(".jpg")
    assert (image_directory / first).read_bytes() == b"image"


def test_empty_upload_keeps_existing_image(app, image_directory):
    old = image_directory / "old.jpg"
    old.write_bytes(b"old")
    with app.app_context():
        assert ImageHandler.save_image(upload("")) is None
        assert ImageHandler.update_image("old.jpg", upload("")) == "old.jpg"
    assert old.read_bytes() == b"old"


def test_update_replaces_image(app, image_directory):
    old = image_directory / "old.jpg"
    old.write_bytes(b"old")
    with app.app_context():
        name = ImageHandler.update_image("old.jpg", upload(contents=b"new"))
    assert not old.exists()
    assert (image_directory / name).read_bytes() == b"new"


def test_failed_save_preserves_old_image(app, image_directory, monkeypatch):
    old = image_directory / "old.jpg"
    old.write_bytes(b"old")
    image = upload()
    monkeypatch.setattr(image, "save", lambda path: (_ for _ in ()).throw(OSError("disk full")))
    with app.app_context(), pytest.raises(OSError):
        ImageHandler.update_image(old.name, image)
    assert old.read_bytes() == b"old"


def test_delete_and_fallback(app, image_directory):
    image = image_directory / "photo.jpg"
    image.write_bytes(b"image")
    with app.app_context():
        assert ImageHandler.get_image_path(image.name) == image
        ImageHandler.delete_image(image.name)
        ImageHandler.delete_image(image.name)
        ImageHandler.delete_image(None)
        assert ImageHandler.get_image_path(image.name) == image_directory.parent / "no_photo.jpg"
    assert not image.exists()
