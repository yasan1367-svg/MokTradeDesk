from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)


# ═════════════════════════════════════════════
# فاز ۴۲.۲: PRAGMAهای SQLite برای ایمنی داده
# ═════════════════════════════════════════════
# - foreign_keys=ON : اعمال قیدهای FK (پیش‌تر خاموش بود ⇒ دادهٔ ناسازگار ممکن بود)
# - journal_mode=WAL : خواندن هم‌زمان با نوشتن + مقاومت بهتر در برابر crash
# - busy_timeout=5000 : در قفل موقت، ۵ ثانیه صبر کن (به‌جای خطای فوری)
def _apply_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def enable_sqlite_pragmas(target_engine):
    """ثبت PRAGMAها روی یک engine دلخواه (برای engineهای موقت/تستی)."""
    event.listen(target_engine, "connect", _apply_sqlite_pragmas)
    return target_engine


event.listen(engine, "connect", _apply_sqlite_pragmas)



SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()