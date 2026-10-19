"""تست‌های فاز ۵۳.۶ — بکاپ (DB + تصاویر) و تنظیمات.

- ۵۳.۶.۴: Backup کامل باید تصاویر screenshot را هم دربر بگیرد.
- ۵۳.۶.۳: تنظیمات (theme/timezone/...) باید ذخیره و بازگردانده شوند.
"""
import os
import zipfile

from app.services import backup_service as bs


def test_backup_includes_screenshots(tmp_path, monkeypatch):
    """Backup کامل (zip) باید دیتابیس + فایل‌های screenshots را شامل شود."""
    backups = tmp_path / "backups"
    backups.mkdir()
    shots = tmp_path / "screenshots"
    shots.mkdir()
    (shots / "sub").mkdir()

    monkeypatch.setattr(bs, "BACKUP_DIR", str(backups))
    monkeypatch.setattr(bs, "CONFIG_PATH", str(backups / ".backup_config.json"))
    monkeypatch.setattr(bs, "STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(bs, "SCREENSHOTS_DIR", str(shots))

    (shots / "shot1.png").write_bytes(b"PNG-DATA")
    (shots / "sub" / "shot2.png").write_bytes(b"PNG2")

    info = bs.create_backup_archive()
    assert info["filename"].endswith(".zip")
    assert info["db_filename"].endswith(".db")
    assert info["screenshots_count"] == 2

    path = os.path.join(bs.BACKUP_DIR, info["filename"])
    assert os.path.exists(path)
    with zipfile.ZipFile(path) as zf:
        names = [n.replace("\\", "/") for n in zf.namelist()]

    assert any(n.startswith("trading_desk_") and n.endswith(".db") for n in names)
    assert "screenshots/shot1.png" in names
    assert "screenshots/sub/shot2.png" in names


def test_settings_roundtrip(client):
    """تنظیمات (theme/timezone/currency/calendar) باید ذخیره و بازخوانی شوند."""
    r = client.patch("/api/settings/", json={
        "theme": "dark",
        "timezone": "Asia/Tehran",
        "currency": "IRR",
        "calendar": "jalali",
    })
    assert r.status_code == 200, r.text

    body = client.get("/api/settings/").json()
    assert body["theme"] == "dark"
    assert body["timezone"] == "Asia/Tehran"
    assert body["currency"] == "IRR"
    assert body["calendar"] == "jalali"
