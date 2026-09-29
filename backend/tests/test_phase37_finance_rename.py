"""تست‌های Phase 37 — Financial Rename & Enum Extension.

پوشش:
- rename کلاس‌ها (`Account`→`FinancialAccount`, `Transaction`→`FinancialTransaction`)
- حفظ `__tablename__` (بدون migration)
- aliasهای سازگاری
- مقادیر جدید Enumها (`CONVERSION`, `TRANSFER`, `ADJUSTMENT`)
- سلامت relationshipها و endpointهای مالی موجود
"""
from app.models.finance import (
    Account,
    AccountType,
    Category,
    CategoryType,
    Currency,
    FinancialAccount,
    FinancialTransaction,
    Transaction,
    TransactionType,
)


# ═════════════════════════════════════════════
# rename + alias
# ═════════════════════════════════════════════
def test_aliases_are_identical():
    assert Account is FinancialAccount
    assert Transaction is FinancialTransaction


def test_tablenames_unchanged_no_migration():
    """فاز ۳۷: نام جدول‌ها عوض نشده ⇒ هیچ migration/rebuild لازم نیست."""
    assert FinancialAccount.__tablename__ == "accounts"
    assert FinancialTransaction.__tablename__ == "transactions"
    assert Category.__tablename__ == "categories"


def test_fk_targets_still_point_to_accounts():
    fks = {fk.target_fullname for fk in FinancialTransaction.__table__.foreign_keys}
    assert "accounts.id" in fks
    assert "categories.id" in fks


# ═════════════════════════════════════════════
# Enumها
# ═════════════════════════════════════════════
def test_category_type_has_conversion_and_keeps_exchange():
    values = {e.value for e in CategoryType}
    assert "conversion" in values
    assert "exchange" in values  # سازگاری با داده/کد قدیمی
    assert CategoryType.CONVERSION.value == "conversion"


def test_transaction_type_has_transfer_and_adjustment():
    values = {e.value for e in TransactionType}
    assert "transfer" in values
    assert "adjustment" in values
    # مقادیر قبلی دست‌نخورده
    for old in ("deposit", "withdrawal", "exchange", "profit", "loss", "fee", "purchase"):
        assert old in values


# ═════════════════════════════════════════════
# رفتار مدل (relationshipها با نام جدید)
# ═════════════════════════════════════════════
def test_relationships_with_renamed_classes(db_session):
    acc = FinancialAccount(name="Trust Wallet", type=AccountType.CRYPTO_WALLET,
                           currency=Currency.USD, balance=0.0)
    other = FinancialAccount(name="Bank", type=AccountType.BANK,
                             currency=Currency.USD, balance=0.0)
    db_session.add_all([acc, other])
    db_session.commit()

    tx = FinancialTransaction(
        account_id=other.id, amount=100.0, currency=Currency.USD,
        type=TransactionType.TRANSFER,
        from_account_id=acc.id, to_account_id=other.id,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    # relationshipهای دوطرفه
    assert tx.from_account.id == acc.id
    assert tx.to_account.id == other.id
    assert tx in other.entries
    assert tx in acc.transactions_out
    assert tx in other.transactions_in


def test_new_enum_values_are_persistable(db_session):
    acc = FinancialAccount(name="Exchange", type=AccountType.EXCHANGE,
                           currency=Currency.IRR, balance=0.0)
    cat = Category(name="تبدیل ارز", type=CategoryType.CONVERSION)
    db_session.add_all([acc, cat])
    db_session.commit()

    tx = FinancialTransaction(
        account_id=acc.id, category_id=cat.id, amount=50_000_000.0,
        currency=Currency.IRR, type=TransactionType.ADJUSTMENT,
    )
    db_session.add(tx)
    db_session.commit()
    db_session.refresh(tx)

    assert tx.type == TransactionType.ADJUSTMENT
    assert tx.category.type == CategoryType.CONVERSION


# ═════════════════════════════════════════════
# سازگاری API (بدون تغییر path/JSON)
# ═════════════════════════════════════════════
def test_finance_endpoints_still_work_after_rename(client):
    acc_id = client.post(
        "/api/finance/accounts", json={"name": "A", "type": "bank"}
    ).json()["id"]
    assert client.get("/api/finance/accounts").status_code == 200

    r = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 500, "type": "deposit",
    })
    assert r.status_code == 200

    rows = client.get("/api/finance/transactions").json()
    assert len(rows) == 1
    assert rows[0]["type"] == "deposit"
    assert rows[0]["account_name"] == "A"

    # نوع جدید هم از API قابل استفاده است
    r2 = client.post("/api/finance/transactions", json={
        "account_id": acc_id, "amount": 250, "type": "adjustment",
    })
    assert r2.status_code == 200
    assert client.get("/api/finance/summary").status_code == 200


def test_category_crud_with_conversion(client):
    r = client.post("/api/finance/categories", json={"name": "C", "type": "conversion"})
    assert r.status_code == 200
    assert any(c["type"] == "conversion" for c in client.get("/api/finance/categories").json())
