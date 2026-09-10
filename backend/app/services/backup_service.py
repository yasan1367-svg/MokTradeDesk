import os
import shutil
import zipfile
from datetime import datetime
from typing import Optional


class BackupService:
    BACKUP_DIR = "backups"
    DB_FILE = "trading_desk.db"
    UPLOADS_DIR = "uploads"

    @classmethod
    def create_backup(cls) -> Optional[str]:
        """
        ایجاد نسخه پشتیبان ZIP از دیتابیس SQLite و پوشه اسکرین‌شات‌ها
        """
        os.makedirs(cls.BACKUP_DIR, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_MokTradeDesk_{timestamp}.zip"
        backup_path = os.path.join(cls.BACKUP_DIR, backup_filename)

        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # ۱. پشتیبان‌گیری از فایل دیتابیس
                db_paths = [cls.DB_FILE, os.path.join("backend", cls.DB_FILE)]
                for db in db_paths:
                    if os.path.exists(db):
                        zipf.write(db, arcname=cls.DB_FILE)
                        break

                # ۲. پشتیبان‌گیری از پوشه اسکرین‌شات‌ها
                uploads_path = cls.UPLOADS_DIR if os.path.exists(cls.UPLOADS_DIR) else os.path.join("backend", cls.UPLOADS_DIR)
                if os.path.exists(uploads_path):
                    for root, _, files in os.walk(uploads_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, start=os.path.dirname(uploads_path))
                            zipf.write(file_path, arcname=arcname)

            print(f"✅ پشتیبان‌گیری با موفقیت انجام شد: {backup_path}")
            return backup_path
        except Exception as e:
            print(f"❌ خطا در ایجاد نسخه پشتیبان: {str(e)}")
            return None