"""
APIهای Backup دیتابیس (فاز ۱۷)

POST   /api/backup/create              — ساخت Backup دستی
GET    /api/backup/list                — لیست Backupها
GET    /api/backup/download/{filename} — دانلود Backup
POST   /api/backup/restore/{filename}  — بازیابی
DELETE /api/backup/{filename}          — حذف Backup
GET    /api/backup/settings            — تنظیمات Backup خودکار
PUT    /api/backup/settings            — ذخیرهٔ تنظیمات Backup خودکار
"""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from ..services import backup_service as svc

router = APIRouter()


class BackupConfigUpdate(BaseModel):
    auto_enabled: Optional[bool] = None
    interval_hours: Optional[int] = None
    keep: Optional[int] = None


@router.post("/create")
def create_backup():
    """ساخت Backup دستی"""
    try:
        return svc.create_backup()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
def list_backups():
    """لیست Backupهای موجود"""
    return svc.list_backups()


@router.get("/settings")
def get_backup_settings():
    """تنظیمات فعلی Backup خودکار"""
    return svc.load_config()


@router.put("/settings")
def update_backup_settings(data: BackupConfigUpdate):
    """ذخیرهٔ تنظیمات Backup خودکار"""
    return svc.save_config(data.model_dump(exclude_unset=True))


@router.get("/download/{filename}")
def download_backup(filename: str):
    """دانلود فایل Backup"""
    try:
        name = svc.safe_name(filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    path = os.path.join(svc.BACKUP_DIR, name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="فایل Backup پیدا نشد")

    return FileResponse(path, media_type="application/octet-stream", filename=name, headers={"Content-Disposition": f'attachment; filename="{name}"'})


@router.post("/restore/{filename}")
def restore_backup(filename: str):
    """بازیابی دیتابیس از یک Backup (خطرناک — قبل از آن Backup ایمنی گرفته می‌شود)"""
    try:
        return svc.restore_backup(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{filename}")
def delete_backup(filename: str):
    """حذف یک Backup"""
    try:
        return svc.delete_backup(filename)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
