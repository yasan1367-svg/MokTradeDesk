"""Phase 36 — Performance Benchmark (1K / 10K / 100K / 500K).

اندازه‌گیری ۵ ناحیه:
  1) Dashboard          2) Trade List       3) Analysis
  4) Prop Calculation   5) Finance Reports

اجرا:
    cd backend
    venv\\Scripts\\python.exe benchmarks\\bench_phase36.py
    venv\\Scripts\\python.exe benchmarks\\bench_phase36.py --sizes 1000,10000
    venv\\Scripts\\python.exe benchmarks\\bench_phase36.py --sizes 500000 --skip-analysis
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import app.main  # noqa: E402,F401  (ثبت همهٔ مدل‌ها در Base.metadata)
from app.core.database import Base  # noqa: E402
from app.models.finance import (  # noqa: E402
    FinancialAccount, AccountType, Category, CategoryType, Currency, FinancialTransaction,
    TransactionType,
)
from app.models.prop import (  # noqa: E402
    PropAccount, PropFirm, PropStage, StageStatus, StageType,
)
from app.models.strategy import (  # noqa: E402
    Strategy, StrategyVersion, TestType, Trade, TradeSource,
)

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
BATCH = 10_000

INDEXES = {
    "trades": [
        "prop_stage_id", "personal_trading_account_id", "is_deleted", "close_time",
    ],
    "transactions": ["account_id", "date", "type"],
}


def _fmt(ms: float) -> str:
    return f"{ms:,.1f} ms"


def timed(label: str, fn):
    t0 = time.perf_counter()
    out = fn()
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"    {label:<32} {_fmt(elapsed):>14}")
    return out, elapsed


def drop_indexes(engine) -> None:
    with engine.begin() as conn:
        for table, cols in INDEXES.items():
            for col in cols:
                conn.execute(text(f"DROP INDEX IF EXISTS ix_{table}_{col}"))


def create_indexes(engine) -> float:
    t0 = time.perf_counter()
    with engine.begin() as conn:
        for table, cols in INDEXES.items():
            for col in cols:
                conn.execute(
                    text(f"CREATE INDEX IF NOT EXISTS ix_{table}_{col} ON {table} ({col})")
                )
    return (time.perf_counter() - t0) * 1000


def seed(db, n: int) -> dict:
    """درج سریع N معامله + یک مرحلهٔ پراپ + یک حساب مالی با تراکنش‌ها."""
    strat = Strategy(name="bench")
    db.add(strat)
    db.flush()
    version = StrategyVersion(strategy_id=strat.id, version_name="v1")
    db.add(version)
    db.flush()

    firm = PropFirm(name="BENCH")
    db.add(firm)
    db.flush()
    acc = PropAccount(prop_firm_id=firm.id, account_label="P1")
    db.add(acc)
    db.flush()
    stage = PropStage(
        prop_account_id=acc.id, stage_type=StageType.FUNDED_REAL,
        status=StageStatus.ACTIVE, initial_balance=10000.0,
        profit_target=1000.0, max_daily_dd=500.0, max_total_dd=1000.0,
        min_trading_days=5, profit_share_percentage=80.0, total_withdrawn=0.0,
    )
    db.add(stage)
    db.flush()

    fin_acc = FinancialAccount(name="Bank", type=AccountType.BANK, currency=Currency.USD, balance=0.0)
    cat = Category(name="سود معاملات", type=CategoryType.INCOME)
    db.add_all([fin_acc, cat])
    db.commit()
    db.refresh(fin_acc)
    db.refresh(cat)

    rnd = random.Random(42)
    base = datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)

    for start in range(0, n, BATCH):
        rows = []
        for i in range(start, min(start + BATCH, n)):
            is_prop = i % 10 == 0
            open_t = base + timedelta(minutes=17 * i)
            rows.append({
                "version_id": version.id,
                "prop_stage_id": stage.id if is_prop else None,
                "symbol": SYMBOLS[i % len(SYMBOLS)],
                "direction": "buy" if i % 2 == 0 else "sell",
                "open_time": open_t,
                "close_time": open_t + timedelta(minutes=45),
                "open_price": 2000.0 + (i % 100),
                "close_price": 2000.0 + (i % 100) + rnd.choice([-5, -2, 2, 5]),
                "size": 0.1 + (i % 5) * 0.1,
                "pnl": round(rnd.uniform(-400, 600), 2),
                "commission": -1.0,
                "swap": 0.0,
                "source": TradeSource.MANUAL.name,
                "test_type": TestType.REAL_PROP.name if is_prop else TestType.BACKTEST.name,
                "is_deleted": 0,
            })
        db.bulk_insert_mappings(Trade, rows)
        db.commit()

    # تراکنش‌های مالی (۵٪ تعداد، سقف ۲۰۰۰)
    tx_rows = []
    for i in range(min(2000, max(1, n // 20))):
        tx_rows.append({
            "account_id": fin_acc.id,
            "category_id": cat.id,
            "amount": round(rnd.uniform(10, 900), 2),
            "currency": Currency.USD.name,
            "date": base + timedelta(hours=i),
            "description": f"tx {i}",
            "type": TransactionType.PROFIT.name,
            "is_deleted": 0,
        })
    db.bulk_insert_mappings(FinancialTransaction, tx_rows)
    db.commit()

    return {"version_id": version.id, "stage_id": stage.id, "account_id": fin_acc.id}


def run_benchmarks(db, ctx: dict, skip_analysis: bool) -> None:
    from app.api.analytics import get_dashboard_data
    from app.api.finance import get_finance_summary, get_money_cycle, get_transactions
    from app.api.prop import list_payouts
    from app.api.trades import get_trades
    from app.services.analysis_service import AnalysisService
    from app.services.prop_rule_engine import PropRuleEngine

    print("  ── ۱) Dashboard ──")
    timed("GET /api/analytics/dashboard", lambda: get_dashboard_data(db=db))

    print("  ── ۲) Trade List (Pagination) ──")
    timed("GET /api/trades/ page=1 size=50", lambda: get_trades(db=db, page=1, page_size=50))
    timed("GET /api/trades/ prop_stage", lambda: get_trades(db=db, prop_stage_id=ctx["stage_id"]))

    print("  ── ۳) Analysis ──")
    if skip_analysis:
        print("    (skipped)")
    else:
        timed("analyze_version", lambda: AnalysisService(db).analyze_version(ctx["version_id"]))

    print("  ── ۴) Prop Calculation ──")
    timed("evaluate_stage (single)", lambda: PropRuleEngine.evaluate_stage(db, ctx["stage_id"]))
    timed("evaluate_stages (bulk x1)", lambda: PropRuleEngine.evaluate_stages(db, [ctx["stage_id"]]))

    print("  ── ۵) Finance Reports ──")
    timed("GET /api/finance/summary", lambda: get_finance_summary(db=db))
    timed("GET /api/finance/money-cycle", lambda: get_money_cycle(db=db))
    timed("GET /api/finance/transactions l=100", lambda: get_transactions(
        date_from=None, date_to=None, account_id=None, type=None, category_id=None,
        limit=100, offset=0, db=db,
    ))
    timed("GET /api/prop/payouts l=100", lambda: list_payouts(
        firm_id=None, currency=None, date_from=None, date_to=None,
        limit=100, offset=0, db=db,
    ))


def _time(fn) -> float:
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000


def index_impact(engine, db, ctx: dict) -> None:
    """مقایسهٔ کوئری‌های کلیدی قبل/بعد از ساخت ایندکس‌های فاز ۳۶."""
    from app.api.trades import get_trades

    def run() -> dict:
        return {
            "prop_stage filter": _time(
                lambda: get_trades(db=db, prop_stage_id=ctx["stage_id"])
            ),
            "recent closed (close_time)": _time(
                lambda: db.query(Trade)
                .filter(Trade.is_deleted == False, Trade.close_time.isnot(None))
                .order_by(Trade.close_time.desc())
                .limit(50)
                .all()
            ),
            "deleted filter (is_deleted)": _time(
                lambda: db.query(Trade).filter(Trade.is_deleted == False).count()
            ),
        }

    db.expire_all()
    drop_indexes(engine)
    db.expire_all()
    before = run()

    build_ms = create_indexes(engine)
    db.expire_all()
    after = run()

    print("  ── Index Impact (بدون ایندکس → با ایندکس) ──")
    for key in before:
        b, a = before[key], after[key]
        speed = (b / a) if a else 0.0
        print(f"    {key:<30} {_fmt(b):>13} → {_fmt(a):>13}   x{speed:.1f}")
    print(f"    {'index build':<30} {'':>13}   {_fmt(build_ms):>13}")


def bench_size(n: int, skip_analysis: bool, do_index_impact: bool = False) -> None:
    path = os.path.abspath(f"_bench_phase36_{n}.db")
    if os.path.exists(path):
        os.remove(path)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    print(f"\n{'=' * 62}\n📊 N = {n:,} trades   (DB: {os.path.basename(path)})\n{'=' * 62}")
    drop_indexes(engine)

    Session = sessionmaker(bind=engine, autoflush=False)
    db = Session()
    t0 = time.perf_counter()
    ctx = seed(db, n)
    print(f"  seed: {time.perf_counter() - t0:,.1f} s")
    print(f"  index build: {_fmt(create_indexes(engine))}")

    with engine.begin() as conn:
        conn.execute(text("ANALYZE"))

    run_benchmarks(db, ctx, skip_analysis)

    if do_index_impact:
        index_impact(engine, db, ctx)

    db.close()
    engine.dispose()
    if os.path.exists(path):
        os.remove(path)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1000,10000,100000,500000")
    ap.add_argument("--skip-analysis", action="store_true")
    ap.add_argument("--index-impact", action="store_true",
                    help="مقایسهٔ کوئری‌ها قبل/بعد از ساخت ایندکس‌های فاز ۳۶")
    args = ap.parse_args()

    sizes = [int(s) for s in args.sizes.replace(" ", "").split(",") if s]
    for n in sizes:
        bench_size(n, args.skip_analysis, args.index_impact)


if __name__ == "__main__":
    main()

