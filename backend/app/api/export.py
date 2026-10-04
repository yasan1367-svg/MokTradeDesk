import io
import csv
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from ..core.database import get_db
from ..core.rate_limit import limiter, EXPORT_RATE_LIMIT
from ..models.strategy import Trade, StrategyVersion
from ..services.analysis_service import AnalysisService
from ..services import metrics
from ..utils.chart_helpers import draw_equity_chart, draw_win_loss_pie, get_font_path
from ..utils.trade_scope import analysis_trades_filter
from ..utils.date_range import filter_by_range
# ═════════════════════════════════════════════
# Font Registration (Vazirmatn) + Persian Date
# ═════════════════════════════════════════════
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import jdatetime
import os
import arabic_reshaper
from bidi.algorithm import get_display
_VAZIR_PATH = get_font_path("regular")
_VAZIR_BOLD_PATH = get_font_path("bold")
try:
    if _VAZIR_PATH and os.path.exists(_VAZIR_PATH):
        pdfmetrics.registerFont(TTFont("Vazirmatn", _VAZIR_PATH))
        pdfmetrics.registerFont(TTFont("Vazirmatn-Bold", _VAZIR_BOLD_PATH))
        _PERSIAN_FONT = "Vazirmatn"
    else:
        _PERSIAN_FONT = "Helvetica"
except Exception:
    _PERSIAN_FONT = "Helvetica"
def _pdate(dt=None):
    """تاریخ شمسی"""
    if dt is None:
        dt = datetime.now(timezone.utc)
    j = jdatetime.datetime.fromgregorian(datetime=dt)
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
              "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
    return f"{j.day} {months[j.month - 1]} {j.year}"
def _fa(text):
    """Reshape Persian/Arabic text for correct rendering in reportlab"""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)
router = APIRouter()
def _add_chart_image(chart_buf: io.BytesIO, width=400, height=160):
    """تبدیل BytesIO نمودار به Image flowable برای درج در PDF"""
    from reportlab.platypus import Image
    chart_buf.seek(0)
    return Image(chart_buf, width=width, height=height)
def _colored_pnl(value, fmt=".2f"):
    """رنگ‌آمیزی سلول سود/زیان برای جدول با فونت فارسی"""
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph
    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = _PERSIAN_FONT
    style.fontSize = 8
    if value is None or value == "":
        return Paragraph("<font color='#9AA8BF'>-</font>", style)
    v = float(value)
    if v > 0:
        return Paragraph(f"<font color='#13AE81'>+{v:{fmt}}</font>", style)
    elif v < 0:
        return Paragraph(f"<font color='#E45D72'>{v:{fmt}}</font>", style)
    return Paragraph(f"<font color='#6B7A94'>{v:{fmt}}</font>", style)
def _build_pdf_response(buffer, filename_prefix):
    """BytesIO -> StreamingResponse"""
    buffer.seek(0)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename_prefix}_{ts}.pdf"},
    )
def _draw_header(canvas, doc):
    canvas.saveState()
    canvas.setFont(_PERSIAN_FONT, 9)
    canvas.drawString(40, 20, _fa(f"گزارش معاملات | MokTradeDesk \u2014 {_pdate()}"))
    canvas.drawRightString(doc.pagesize[0] - 40, 20, _fa(f"صفحه {doc.page}"))
    canvas.restoreState()
def _draw_table(elements, data, col_widths, title):
    from reportlab.platypus import Table, TableStyle, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    h3 = styles["Heading3"]
    h3.fontName = _PERSIAN_FONT
    if title:
        elements.append(Paragraph(_fa(title), h3))
    td = [data[0]] + [[str(c) if c is not None else "" for c in r] for r in data[1:]]
    t = Table(td, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3F7CFF")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), f"{_PERSIAN_FONT}"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTNAME", (0, 1), (-1, -1), _PERSIAN_FONT),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D0D5DD")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#F9FAFB"), colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
# ═════════════════════════════════════════════
# CSV Export — Trades
# ═════════════════════════════════════════════
@router.get("/trades/csv")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_trades_csv(
    request: Request,
    version_id: Optional[int] = None,
    strategy_id: Optional[int] = None,
    symbol: Optional[str] = None,
    test_type: Optional[str] = None,
    source: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export trades as CSV with optional filters"""
    query = db.query(Trade).options(joinedload(Trade.version).joinedload(StrategyVersion.strategy))
    # فاز ۲۵: معاملات حذف‌شده در خروجی نمی‌آیند
    if version_id: query = query.filter(Trade.version_id == version_id)
    if strategy_id: query = query.join(StrategyVersion, Trade.version_id == StrategyVersion.id).filter(StrategyVersion.strategy_id == strategy_id)
    if symbol: query = query.filter(Trade.symbol == symbol)
    if test_type: query = query.filter(Trade.test_type == test_type)
    if source: query = query.filter(Trade.source == source)
    if direction: query = query.filter(Trade.direction == direction)
    if search: query = query.filter(Trade.note.like(f"%{search}%"))
    # فاز ۵۳.۵.۳: بازهٔ تاریخ **شامل آخرین روز** (نیمه‌باز) — سازگار با بقیهٔ گزارش‌ها
    query = filter_by_range(query, Trade.open_time, date_from, date_to)
    trades = query.order_by(Trade.close_time.desc()).all()
    output = io.StringIO()
    w = csv.writer(output)
    w.writerow(["ID","Symbol","Direction","Size","Open Price","Close Price","Open Time","Close Time","PnL","Commission","Swap","Net PnL","R Multiple","Source","Test Type","Strategy","Version","Note"])
    for t in trades:
        sn = t.version.strategy.name if t.version and t.version.strategy else ""
        vn = t.version.version_name if t.version else ""
        w.writerow([t.id, t.symbol, t.direction, t.size, t.open_price, t.close_price,
            t.open_time.isoformat() if t.open_time else "",
            t.close_time.isoformat() if t.close_time else "",
            t.pnl, t.commission, t.swap, round(t.net_pnl, 2), t.r_multiple,
            t.source.value if t.source else "",
            t.test_type.value if t.test_type else "", sn, vn, t.note or ""])
    output.seek(0)
    fn = f"trades_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fn}"},
    )
# ═════════════════════════════════════════════
# PDF Export — Trades
# ═════════════════════════════════════════════
@router.get("/trades/pdf")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_trades_pdf(
    request: Request,
    version_id: Optional[int] = None,
    strategy_id: Optional[int] = None,
    symbol: Optional[str] = None,
    test_type: Optional[str] = None,
    source: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Export trades as PDF report"""
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
    from reportlab.lib.styles import getSampleStyleSheet
    query = db.query(Trade).options(joinedload(Trade.version).joinedload(StrategyVersion.strategy))
    # فاز ۲۵: معاملات حذف‌شده در خروجی نمی‌آیند
    if version_id: query = query.filter(Trade.version_id == version_id)
    if strategy_id: query = query.join(StrategyVersion, Trade.version_id == StrategyVersion.id).filter(StrategyVersion.strategy_id == strategy_id)
    if symbol: query = query.filter(Trade.symbol == symbol)
    if test_type: query = query.filter(Trade.test_type == test_type)
    if source: query = query.filter(Trade.source == source)
    if direction: query = query.filter(Trade.direction == direction)
    if search: query = query.filter(Trade.note.like(f"%{search}%"))
    # فاز ۵۳.۵.۳: بازهٔ تاریخ **شامل آخرین روز** (نیمه‌باز) — سازگار با بقیهٔ گزارش‌ها
    query = filter_by_range(query, Trade.open_time, date_from, date_to)
    trades = query.order_by(Trade.close_time.desc()).all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=0.5 * inch, rightMargin=0.5 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    els = []
    els.append(Paragraph(_fa("گزارش معاملات"), styles["Title"]))
    styles["Title"].fontName = _PERSIAN_FONT
    styles["Title"].fontSize = 20
    els.append(Spacer(1, 8))
    n = styles["Normal"]
    n.fontName = _PERSIAN_FONT
    n.fontSize = 9
    els.append(Paragraph(
        _fa(f"تعداد کل: {len(trades)} معامله | تاریخ گزارش: {_pdate()}"),
        n,
    ))
    els.append(Spacer(1, 20))
    # نمودارها
    try:
        equity_img = _add_chart_image(draw_equity_chart(trades), width=460, height=170)
        pie_img = _add_chart_image(draw_win_loss_pie(trades), width=170, height=170)
        chart_table = Table(
            [[equity_img, pie_img]],
            colWidths=[480, 180],
        )
        els.append(chart_table)
        els.append(Spacer(1, 20))
    except Exception:
        els.append(Spacer(1, 20))
    header = ["ID", "Symbol", "Dir", "Size", "Open USDT ", "Close USDT ", "Open Time", "Close Time", "Net PnL", "Gross", "Comm.", "Swap", "R"]
    rows = [header]
    for t in trades:
        rows.append([
            t.id, t.symbol, "Buy" if t.direction == "buy" else "Sell",
            t.size, t.open_price, t.close_price or "",
            t.open_time.strftime("%Y-%m-%d %H:%M") if t.open_time else "",
            t.close_time.strftime("%Y-%m-%d %H:%M") if t.close_time else "",
            round(t.net_pnl, 2) if t.net_pnl is not None else "",
            round(t.pnl, 2) if t.pnl is not None else "",
            t.commission or 0, t.swap or 0,
            round(t.r_multiple, 2) if t.r_multiple is not None else "",
        ])
    _draw_table(els, rows, [30, 50, 40, 35, 55, 55, 100, 100, 50, 40, 40, 50], _fa("لیست معاملات"))
    # Summary
    els.append(Spacer(1, 30))
    els.append(Paragraph(_fa("خلاصه آماری"), styles["Heading2"]))
    styles["Heading2"].fontName = _PERSIAN_FONT
    closed = [t for t in trades if t.close_time]
    if closed:
        # فاز ۴۳: خلاصهٔ آماری از تعریف واحد net_pnl
        nets = [metrics.net_pnl(t) for t in closed]
        net = sum(nets)
        wins = [n for n in nets if n > 0]
        losses = [n for n in nets if n < 0]
        wr = len(wins) / len(closed) * 100
        gp = sum(wins)
        gl = abs(sum(losses))
        pf = gp / gl if gl > 0 else (100.0 if gp > 0 else 0.0)
    else:
        net = wr = pf = 0
    _draw_table(els, [
        [_fa("شاخص"), _fa("مقدار")],
        [_fa("سود خالص"), f"{net:.2f} USDT "],
        [_fa("نرخ برد"), f"{wr:.1f}%"],
        [_fa("فاکتور سود"), f"{pf:.2f}"],
        [_fa("کل معاملات"), str(len(closed))],
    ], [150, 150], "")
    doc.build(els, onFirstPage=_draw_header, onLaterPages=_draw_header)
    return _build_pdf_response(buffer, "trades")
# ═════════════════════════════════════════════
# PDF Export — Analysis Report
# ═════════════════════════════════════════════
@router.get("/analysis/pdf")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_analysis_pdf(
    request: Request,
    version_id: int = Query(..., description="Version ID for analysis report"),
    test_type: Optional[str] = Query("BACKTEST", description="BACKTEST | FORWARD"),
    db: Session = Depends(get_db),
):
    """Export version analysis as PDF — فاز ۵۳.۵.۲: پشتیبانی از `test_type`"""
    from ..models.strategy import TestType as _TT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    tt = None
    if test_type:
        try:
            tt = _TT(str(test_type).strip().lower())
        except ValueError:
            tt = None
    version = db.query(StrategyVersion).filter(StrategyVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    service = AnalysisService(db)
    try:
        result = service.analyze_version(version_id, tt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
    metrics = result["result"]
    # فاز ۵۳.۵.۲: معاملات هم مطابق `test_type` (Backtest/Forward) فیلتر می‌شوند
    trades_q = db.query(Trade).filter(
        Trade.version_id == version_id
    )
    if tt is not None:
        trades_q = trades_q.filter(Trade.test_type == tt)
    else:
        trades_q = trades_q.filter(analysis_trades_filter())
    trades_list = trades_q.all()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    els = []
    sn = version.strategy.name if version.strategy else "-"
    styles["Title"].fontName = _PERSIAN_FONT
    styles["Title"].fontSize = 17
    styles["Heading2"].fontName = _PERSIAN_FONT
    n = styles["Normal"]
    n.fontName = _PERSIAN_FONT
    n.fontSize = 9
    els.append(Paragraph(_fa(f"گزارش تحلیل: {version.version_name}"), styles["Title"]))
    els.append(Spacer(1, 8))
    els.append(Paragraph(_fa(f"استراتژی: {sn}"), n))
    els.append(Paragraph(_fa(f"تاریخ گزارش: {_pdate()}"), n))
    els.append(Spacer(1, 20))
    # نمودارها
    try:
        equity_img = _add_chart_image(draw_equity_chart(trades_list), width=300, height=140)
        pie_img = _add_chart_image(draw_win_loss_pie(trades_list), width=140, height=140)
        from reportlab.platypus import Table as T
        els.append(T([[equity_img, pie_img]], colWidths=[320, 160]))
        els.append(Spacer(1, 15))
    except Exception:
        els.append(Spacer(1, 15))
    els.append(Paragraph(_fa("متریک‌های کلیدی"), styles["Heading2"]))
    _draw_table(els, [
        [_fa("شاخص"), _fa("مقدار")],
        [_fa("کل معاملات"), str(metrics.total_trades)],
        [_fa("نرخ برد"), f"{metrics.win_rate:.1f}%"],
        [_fa("فاکتور سود"), f"{metrics.profit_factor:.2f}"],
        [_fa("سود خالص"), f"{metrics.net_pnl:.2f} USDT "],
        [_fa("نتیجه R"), f"{metrics.net_r:.2f} R"],
        [_fa("حداکثر ضرر"), f"{metrics.max_dd:.2f} USDT "],
        [_fa("میانگین هر معامله"), f"{metrics.expectancy:.2f} USDT "],
        [_fa("اکسپکتنسی R"), f"{metrics.expectancy_r:.2f} R" if metrics.expectancy_r else "-"],
        [_fa("میانگین برد"), f"{metrics.avg_win:.2f} USDT "],
        [_fa("میانگین باخت"), f"{metrics.avg_loss:.2f} USDT "],
        [_fa("بزرگ‌ترین برد"), f"{metrics.largest_win:.2f} USDT "],
        [_fa("بزرگ‌ترین باخت"), f"{metrics.largest_loss:.2f} USDT "],
        [_fa("بیشترین باخت متوالی"), str(metrics.max_consecutive_losses)],
    ], [200, 200], "")
    els.append(Spacer(1, 30))
    if trades_list:
        els.append(Paragraph(_fa("معاملات"), styles["Heading2"]))
        td = [["ID", _fa("نماد"), _fa("جهت"), _fa("حجم"), _fa("سود خالص"), _fa("سود ناخالص")]]
        for t in trades_list[:50]:
            td.append([
                t.id, t.symbol, _fa("خرید" if t.direction == "buy" else "فروش"),
                t.size, round(t.net_pnl, 2) if t.net_pnl else "", round(t.pnl, 2) if t.pnl else "",
            ])
        _draw_table(els, td, [40, 60, 40, 50, 60, 60], "")
        if len(trades_list) > 50:
            els.append(Paragraph(
                _fa(f"* نمایش ۵۰ معامله از {len(trades_list)} معامله"),
                styles["Italic"],
            ))
    doc.build(els, onFirstPage=_draw_header, onLaterPages=_draw_header)
    return _build_pdf_response(buffer, "analysis")
# ═════════════════════════════════════════════
# PDF Export — Dashboard Summary
# ═════════════════════════════════════════════
@router.get("/dashboard/pdf")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_dashboard_pdf(request: Request, db: Session = Depends(get_db)):
    """Export dashboard summary as PDF"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from ..api.analytics import get_dashboard_data
    dashboard_data = get_dashboard_data(db)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    styles["Title"].fontName = _PERSIAN_FONT
    styles["Title"].fontSize = 17
    styles["Heading2"].fontName = _PERSIAN_FONT
    n = styles["Normal"]
    n.fontName = _PERSIAN_FONT
    n.fontSize = 9
    els = []
    els.append(Paragraph(_fa("گزارش خلاصه Dashboard"), styles["Title"]))
    els.append(Spacer(1, 8))
    els.append(Paragraph(_fa(f"تاریخ گزارش: {_pdate()}"), n))
    els.append(Spacer(1, 20))
    if not dashboard_data:
        els.append(Paragraph(_fa("داده‌ای برای نمایش وجود ندارد"), n))
    else:
        s = dashboard_data.get("summary", {})
        els.append(Paragraph(_fa("خلاصه وضعیت"), styles["Heading2"]))
        _draw_table(els, [
            [_fa("شاخص"), _fa("مقدار")],
            [_fa("سود خالص"), f"{s.get('net_pnl', 0):.2f} USDT "],
            [_fa("نرخ برد"), f"{s.get('win_rate', 0):.1f}%"],
            [_fa("فاکتور سود"), f"{s.get('profit_factor', 0):.2f}"],
            [_fa("حداکثر ضرر"), f"{s.get('max_dd', 0):.2f} USDT "],
        ], [200, 200], "")
        els.append(Spacer(1, 15))
        t = dashboard_data.get("today", {})
        els.append(Paragraph(_fa("عملکرد امروز"), styles["Heading2"]))
        _draw_table(els, [
            [_fa("شاخص"), _fa("مقدار")],
            [_fa("سود/زیان"), f"{t.get('pnl', 0):.2f} USDT "],
            [_fa("تعداد معاملات"), str(t.get('trades_count', 0))],
            [_fa("نرخ برد"), f"{t.get('win_rate', 0):.1f}%"],
        ], [200, 200], "")
        els.append(Spacer(1, 15))
        p = dashboard_data.get("periods", {})
        els.append(Paragraph(_fa("عملکرد دوره‌ای"), styles["Heading2"]))
        _draw_table(els, [
            [_fa("دوره"), _fa("سود/زیان")],
            [_fa("ماه جاری"), f"{p.get('month', {}).get('pnl', 0):.2f} USDT "],
            [_fa("فصل جاری"), f"{p.get('quarter', {}).get('pnl', 0):.2f} USDT "],
            [_fa("سال جاری"), f"{p.get('year', {}).get('pnl', 0):.2f} USDT "],
        ], [200, 200], "")
        pp = dashboard_data.get("prop_progress", [])
        if pp:
            els.append(Spacer(1, 15))
            els.append(Paragraph(_fa("وضعیت پراپ"), styles["Heading2"]))
            pr = [[_fa("مرحله"), _fa("وضعیت"), _fa("پیشرفت سود")]]
            for st in pp:
                pr.append([
                    st.get("stage_name", "-"),
                    st.get("status", "-"),
                    f"{st.get('profit_progress_percent', 0):.1f}%",
                ])
            _draw_table(els, pr, [120, 120, 100], "")
    doc.build(els, onFirstPage=_draw_header, onLaterPages=_draw_header)
    return _build_pdf_response(buffer, "dashboard")
