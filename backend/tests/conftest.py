import os
import sys
import tempfile

# ═════════════════════════════════════════════
# فاز ۳۹.۵: جداسازی کامل دیتابیس تست از دیتابیس واقعی
# ═════════════════════════════════════════════
# این تنظیم باید **قبل از** هر import مربوط به `app` انجام شود تا
# `app.core.config.Settings` همین مقدار را بخواند و `app.core.database.engine`
# هرگز به فایل واقعی `trading_desk.db` اشاره نکند (حتی اگر هوک startup اجرا شود).
_TEST_DB_FD, _TEST_DB_PATH = tempfile.mkstemp(prefix="trading_desk_test_", suffix=".db")
os.close(_TEST_DB_FD)
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB_PATH.replace("\\", "/")

# اطمینان از import شدن پکیج app (backend در sys.path)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402  (همه‌ی مدل‌ها/روترها را لود می‌کند)

# ═════════════════════════════════════════════
# غیرفعال‌سازی هوک‌های startup/shutdown (فاز ۳۹.۵)
# ═════════════════════════════════════════════
# هوک `startup` در `app/main.py` برای یک سرویس واقعی طراحی شده و دو عارضهٔ
# جانبی دارد که در تست‌ها ناخواسته‌اند:
#   ۱) `alembic upgrade head` روی DATABASE_URL اجرا می‌کند.
#   ۲) Backup اولیه می‌سازد و thread پس‌زمینهٔ Backup خودکار را روشن می‌کند.
# `TestClient(app)` وقتی به‌صورت context manager استفاده شود رویداد startup را
# اجرا می‌کند ⇒ این هوک‌ها پاک می‌شوند تا تست‌ها هیچ نوشتنی روی فایل واقعی
# دیتابیس انجام ندهند. (تست‌ها جداول را خودشان روی DB درون‌حافظه می‌سازند.)
app.router.on_startup.clear()
app.router.on_shutdown.clear()


@pytest.fixture(scope="function")
def db_session():
    """دیتابیس درون‌حافظه‌ی SQLite برای هر تست"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """کلاینت تست FastAPI با dependency override روی get_db"""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="session", autouse=True)
def _cleanup_test_database():
    """در پایان کل تست‌ها، فایل دیتابیس تستی پاک می‌شود (فاز ۳۹.۵)."""
    yield
    try:
        if os.path.exists(_TEST_DB_PATH):
            os.remove(_TEST_DB_PATH)
    except OSError:
        pass
