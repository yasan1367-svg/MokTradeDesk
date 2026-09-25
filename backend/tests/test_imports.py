"""تست‌های endpointهای ایمپورت — Regression برای arity امضای validate_classification

باگ: `imports.py` تابع `validate_classification` را با ۳ آرگومان صدا می‌زد،
در حالی که امضا ۴ آرگومان دارد: (test_type, version_id, finance_account_id, prop_stage_id)
→ prop_stage_id به‌جای finance_account_id بایند می‌شد و TypeError (کرش ۵۰۰) می‌داد.
"""


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
def _post_mt4(client, **form):
    """آپلود یک فایل HTML خالی در endpoint MT4"""
    return client.post(
        "/api/imports/mt4",
        files={"file": ("report.html", b"<html><body></body></html>", "text/html")},
        data={key: str(value) for key, value in form.items()},
    )


def _post_soft4x(client, **form):
    """آپلود یک فایل xlsx نامعتبر در endpoint Soft4X"""
    return client.post(
        "/api/imports/soft4x",
        files={"file": ("report.xlsx", b"not-an-xlsx", "application/vnd.ms-excel")},
        data={key: str(value) for key, value in form.items()},
    )


# ═════════════════════════════════════════════
# import_mt4 — Classification
# ═════════════════════════════════════════════
def test_import_mt4_backtest_without_version_id(client):
    """BACKTEST بدون version_id باید ۴۰۰ بدهد (نه TypeError ← ۵۰۰)"""
    res = _post_mt4(client, test_type="backtest")
    assert res.status_code == 400
    assert "version_id" in res.json()["detail"]


def test_import_mt4_backtest_with_prop_stage_id(client):
    """prop_stage_id باید در جایگاه خودش بایند شود (نه finance_account_id)"""
    res = _post_mt4(client, test_type="backtest", version_id=1, prop_stage_id=3)
    assert res.status_code == 400
    assert "prop_stage_id" in res.json()["detail"]


def test_import_mt4_real_prop_passes_classification(client):
    """REAL + version_id + prop_stage_id از Classification رد می‌شود"""
    res = _post_mt4(client, test_type="real", version_id=1, prop_stage_id=3)
    # خطا مربوط به مرحله‌ی پارس فایل است، یعنی Classification پاس شده
    assert res.status_code == 400
    assert res.json()["detail"] == "هیچ معامله‌ای در فایل یافت نشد"


# ═════════════════════════════════════════════
# import_soft4x — Classification (همان باگ)
# ═════════════════════════════════════════════
def test_import_soft4x_backtest_without_version_id(client):
    """همین باگ در endpoint Soft4X هم وجود داشت"""
    res = _post_soft4x(client, test_type="backtest")
    assert res.status_code == 400
    assert "version_id" in res.json()["detail"]


def test_import_soft4x_real_prop_passes_classification(client):
    """REAL + version_id + prop_stage_id در Soft4X هم از Classification رد می‌شود"""
    res = _post_soft4x(client, test_type="real", version_id=1, prop_stage_id=3)
    # Classification پاس شده → خطا از پارس فایل xlsx نامعتبر می‌آید
    assert res.status_code == 500
    assert "خطا در پردازش فایل" in res.json()["detail"]
