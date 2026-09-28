from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form, Request
from sqlalchemy.orm import Session
import tempfile
import os
from typing import Optional

from ..core.database import get_db
from ..core.rate_limit import limiter, IMPORT_RATE_LIMIT
from ..services.import_service import Soft4XImporter, MT4Importer
from ..models.strategy import StrategyVersion
from ..utils.trade_validator import TradeValidator
from ..utils.uploads import read_upload_limited

router = APIRouter()


@router.post("/soft4x")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_soft4x(
    request: Request,
    file: UploadFile = File(...),
    version_id: Optional[int] = Form(None),
    prop_stage_id: Optional[int] = Form(None),
    symbol: Optional[str] = Form("XAUUSD"),
    personal_trading_account_id: Optional[int] = Form(None),
    test_type: Optional[str] = Form("backtest"),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.xlsx'):
        raise HTTPException(status_code=400, detail="فایل باید با فرمت xlsx باشد")

    # امضای validate_classification چهار آرگومان دارد:
    # (test_type, version_id, personal_trading_account_id, prop_stage_id)
    # حساب معاملاتی شخصی فقط برای REAL_PERSONAL لازم است
    valid, error = TradeValidator.validate_classification(
        test_type=test_type or "backtest",
        version_id=version_id,
        personal_trading_account_id=personal_trading_account_id,
        prop_stage_id=prop_stage_id,
    )
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_file:
        content = await read_upload_limited(file)
        tmp_file.write(content)
        tmp_path = tmp_file.name

    try:
        importer = Soft4XImporter(db, symbol=symbol, test_type=test_type)
        trades = importer.parse_file(tmp_path)
        target_label = None
        result = None

        if version_id:
            version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
            if not version:
                raise HTTPException(status_code=404, detail="نسخه استراتژی پیدا نشد")
            result = importer.save_trades(
                trades,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
            )
            target_label = "استراتژی"
        elif prop_stage_id:
            result = importer.save_trades(
                trades,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
            )
            target_label = "پراپ"

        if result:
            saved_count = len(result["saved"])
            duplicates_count = len(result["duplicates"])
            if duplicates_count > 0:
                message = f"{saved_count} معامله ذخیره شد ({target_label}) — {duplicates_count} معامله تکراری نادیده گرفته شد"
            else:
                message = f"{saved_count} معامله با موفقیت وارد شد ({target_label})"
        else:
            saved_count = 0
            duplicates_count = 0
            message = f"{len(trades)} معامله شناسایی شد. برای ذخیره، version_id یا prop_stage_id را وارد کنید."

        return {
            "message": message,
            "total_trades": len(trades),
            "saved_trades": saved_count,
            "duplicates_count": duplicates_count,
            "preview": trades[:3]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {str(e)}")

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.post("/mt4")
@limiter.limit(IMPORT_RATE_LIMIT)
async def import_mt4(
    request: Request,
    file: UploadFile = File(...),
    version_id: Optional[int] = Form(None),
    personal_trading_account_id: Optional[int] = Form(None),
    prop_stage_id: Optional[int] = Form(None),
    test_type: Optional[str] = Form("backtest"),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.html'):
        raise HTTPException(status_code=400, detail="فایل باید با فرمت html باشد")

    # امضای validate_classification چهار آرگومان دارد:
    # (test_type, version_id, personal_trading_account_id, prop_stage_id)
    # حساب معاملاتی شخصی فقط برای REAL_PERSONAL لازم است
    valid, error = TradeValidator.validate_classification(
        test_type=test_type or "backtest",
        version_id=version_id,
        personal_trading_account_id=personal_trading_account_id,
        prop_stage_id=prop_stage_id,
    )
    if not valid:
        raise HTTPException(status_code=400, detail=error)

    content = await read_upload_limited(file)

    html_content = None
    for encoding in ['utf-8', 'utf-16', 'windows-1256', 'iso-8859-1', 'cp1252']:
        try:
            html_content = content.decode(encoding)
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if html_content is None:
        raise HTTPException(status_code=400, detail="نمی‌توان فایل را خواند")

    try:
        importer = MT4Importer(db, test_type=test_type)
        trades = importer.parse_html(html_content)

        if not trades:
            raise HTTPException(status_code=400, detail="هیچ معامله‌ای در فایل یافت نشد")

        target_label = None
        result = None

        if version_id:
            version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
            if not version:
                raise HTTPException(status_code=404, detail="نسخه استراتژی پیدا نشد")
            result = importer.save_trades(
                trades,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
            )
            target_label = "استراتژی"
        elif prop_stage_id:
            result = importer.save_trades(
                trades,
                version_id=version_id,
                prop_stage_id=prop_stage_id,
                personal_trading_account_id=personal_trading_account_id,
            )
            target_label = "پراپ"

        if result:
            saved_count = len(result["saved"])
            duplicates_count = len(result["duplicates"])
            if duplicates_count > 0:
                message = f"{saved_count} معامله ذخیره شد ({target_label}) — {duplicates_count} معامله تکراری نادیده گرفته شد"
            else:
                message = f"{saved_count} معامله با موفقیت وارد شد ({target_label})"
        else:
            saved_count = 0
            duplicates_count = 0
            message = f"{len(trades)} معامله شناسایی شد. برای ذخیره، version_id یا prop_stage_id را وارد کنید."

        return {
            "message": message,
            "total_trades": len(trades),
            "saved_trades": saved_count,
            "duplicates_count": duplicates_count,
            "preview": trades[:3]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"خطا در پردازش فایل: {str(e)}")