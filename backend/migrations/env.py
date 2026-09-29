from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ═════════════════════════════════════════════
# Import Base و همه‌ی مدل‌ها
# ═════════════════════════════════════════════
from app.core.database import Base

# Strategy Models
from app.models.strategy import (
    Strategy,
    StrategyVersion,
    Trade,
    CustomTimeInterval,
    TimePoint,
    AnalysisResult,
    AnalysisRun,
    AnalysisScopeRecord,
    SymbolMapping,
)

# Prop Models
from app.models.prop import (
    PropFirm,
    PropFirmDefaultRules,
    PropAccount,
    PropStage,
    PropWithdrawal,
    PropCost,
    PropAlert,
)

# Personal Models (Journal)
from app.models.personal import (
    JournalReview,
    Screenshot,
)

# Settings Models
from app.models.settings import UserSettings

# Finance Models
from app.models.finance import (
    FinancialAccount,
    Category,
    FinancialTransaction,
)

# Trading Models (فاز ۲۸)
from app.models.trading import (
    Broker,
    PersonalTradingAccount,
)

# Import Models (فاز ۳۰/۳۱)
from app.models.imports import (
    ImportProfile,
    ImportBatch,
    ImportBatchRow,
    ImportIdentity,
)

# ═════════════════════════════════════════════
# Alembic Config
# ═════════════════════════════════════════════
config = context.config
# disable_existing_loggers=False تا وقتی Migration درون‌برنامه‌ای (main.py) اجرا می‌شود
# لاگرهای برنامه (moktrade) غیرفعال نشوند.
fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()