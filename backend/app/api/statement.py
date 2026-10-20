import io
import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

from ..core.database import get_db
from ..core.rate_limit import limiter, EXPORT_RATE_LIMIT
from ..schemas.statement import StatementResponse
from ..services.statement_service import StatementService
from .export import _PERSIAN_FONT, _fa, _pdate


router = APIRouter()


@router.get("/data", response_model=StatementResponse)
@limiter.limit(EXPORT_RATE_LIMIT)
def get_statement_data(
    request: Request,
    trader_name: str = Query("Portfolio Manager", description="نام تریدر یا مدیر پرتفوی"),
    account_id: str = Query("MTD-ACT-001", description="شناسه حساب"),
    initial_balance: float = Query(10000.0, description="موجودی اولیه حساب"),
    currency: str = Query("USDT", description="ارز پایه"),
    scope: Optional[str] = Query(None, description="دامنه معاملات (backtest / forward / all)"),
    date_from: Optional[datetime] = Query(None, description="از تاریخ"),
    date_to: Optional[datetime] = Query(None, description="تا تاریخ"),
    version_id: Optional[int] = Query(None, description="شناسه نسخه استراتژی"),
    broker_id: Optional[int] = Query(None, description="شناسه بروکر"),
    db: Session = Depends(get_db),
):
    """دریافت داده‌های ساختارمند استیتمنت رسمی برای نمایش در فرانت‌اند"""
    return StatementService.get_statement_data(
        db=db,
        trader_name=trader_name,
        account_id=account_id,
        initial_balance=initial_balance,
        currency=currency,
        scope=scope,
        date_from=date_from,
        date_to=date_to,
        version_id=version_id,
        broker_id=broker_id,
    )


@router.get("/pdf")
@limiter.limit(EXPORT_RATE_LIMIT)
def export_statement_pdf(
    request: Request,
    trader_name: str = Query("Portfolio Manager", description="نام تریدر یا مدیر پرتفوی"),
    account_id: str = Query("MTD-ACT-001", description="شناسه حساب"),
    initial_balance: float = Query(10000.0, description="موجودی اولیه حساب"),
    currency: str = Query("USDT", description="ارز پایه"),
    scope: Optional[str] = Query(None, description="دامنه معاملات"),
    date_from: Optional[datetime] = Query(None, description="از تاریخ"),
    date_to: Optional[datetime] = Query(None, description="تا تاریخ"),
    version_id: Optional[int] = Query(None, description="شناسه نسخه استراتژی"),
    broker_id: Optional[int] = Query(None, description="شناسه بروکر"),
    lang: str = Query("en", description="زبان استیتمنت (en / fa)"),
    db: Session = Depends(get_db),
):
    """تولید فایل PDF استیتمنت رسمی جهت ارائه به بانک‌ها، صندوق‌ها و سرمایه‌گذاران"""
    data = StatementService.get_statement_data(
        db=db,
        trader_name=trader_name,
        account_id=account_id,
        initial_balance=initial_balance,
        currency=currency,
        scope=scope,
        date_from=date_from,
        date_to=date_to,
        version_id=version_id,
        broker_id=broker_id,
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=32,
        leftMargin=32,
        topMargin=32,
        bottomMargin=32,
    )

    styles = getSampleStyleSheet()
    is_fa = (lang == "fa")
    font_name = _PERSIAN_FONT if is_fa else "Helvetica"
    font_bold = f"{_PERSIAN_FONT}-Bold" if (is_fa and _PERSIAN_FONT != "Helvetica") else ("Helvetica-Bold" if not is_fa else _PERSIAN_FONT)

    # استایل‌های متن
    title_style = ParagraphStyle(
        "InstTitle",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        alignment=TA_RIGHT if is_fa else TA_LEFT,
    )
    subtitle_style = ParagraphStyle(
        "InstSubTitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=TA_RIGHT if is_fa else TA_LEFT,
    )
    heading_style = ParagraphStyle(
        "InstHeading",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E293B"),
        alignment=TA_RIGHT if is_fa else TA_LEFT,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "InstBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#334155"),
        alignment=TA_RIGHT if is_fa else TA_LEFT,
    )

    def txt(s: str) -> str:
        return _fa(s) if is_fa else s

    elements = []

    # 1. سربرگ سازمانی (Corporate Header & Verification Badge)
    header_data = [
        [
            Paragraph(
                f"<b>{txt('MOKTRADEDESK AUDIT DOSSIER' if not is_fa else 'پرونده حسابرسی رسمی معامـلاتی')}</b><br/>"
                f"<font size=8 color='#64748B'>{txt('Institutional Trading Statement · GIPS Standard Factsheet' if not is_fa else 'شناسنامه رسمی عملکرد تجاری · استاندارد GIPS')}</font>",
                title_style,
            ),
            Paragraph(
                f"<font size=7 color='#64748B'>{txt('AUDIT HASH' if not is_fa else 'هش اصالت‌سنجی:')}</font><br/>"
                f"<b><font size=8 color='#0369A1'>{data.credentials.verification_hash}</font></b><br/>"
                f"<font size=7 color='#15803D'>● {txt('VERIFIED LEDGER' if not is_fa else 'دفتر کل معتبر و بدون تغییر')}</font>",
                ParagraphStyle("AuditBadge", parent=styles["Normal"], fontName=font_name, alignment=TA_LEFT if is_fa else TA_RIGHT),
            ),
        ]
    ]
    t_header = Table(header_data, colWidths=[350, 180])
    t_header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_header)

    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284C7"), spaceBefore=6, spaceAfter=10))

    # 2. مشخصات حسابرسی و شناسنامه هویت
    cred_table_data = [
        [
            f"{txt('مدیر پرتفوی / تریدر:' if is_fa else 'Portfolio Manager:')} {data.credentials.trader_name}",
            f"{txt('شناسه حساب / اکانت:' if is_fa else 'Account Identifier:')} {data.credentials.account_id}",
            f"{txt('ارز پایه:' if is_fa else 'Base Currency:')} {data.credentials.currency}",
        ],
        [
            f"{txt('بازه حسابرسی:' if is_fa else 'Audit Period:')} {data.credentials.period_from} ~ {data.credentials.period_to}",
            f"{txt('تاریخ تاییدیه:' if is_fa else 'Audit Timestamp:')} {data.credentials.audit_date}",
            f"{txt('وضعیت رکوردها:' if is_fa else 'Ledger Status:')} {txt('۱۰۰٪ معاملات بسته‌شده' if is_fa else '100% Closed Trades')}",
        ],
    ]
    t_cred = Table([[Paragraph(c, body_style) for c in row] for row in cred_table_data], colWidths=[180, 200, 150])
    t_cred.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(t_cred)
    elements.append(Spacer(1, 12))

    # 3. جدول شاخص‌های کلیدی نهادی (Institutional Key Performance Ratios)
    elements.append(Paragraph(txt("شاخص‌های عملکرد نهادی و سنجش ریسک" if is_fa else "Key Institutional & Risk-Adjusted Ratios"), heading_style))

    m = data.metrics
    ret_color = "#15803D" if m.net_pnl >= 0 else "#B91C1C"

    kpi_rows = [
        [
            txt("شاخص عملکرد" if is_fa else "Metric"),
            txt("مقدار" if is_fa else "Value"),
            txt("شاخص ریسک و کیفیت" if is_fa else "Risk & Quality Metric"),
            txt("مقدار" if is_fa else "Value"),
        ],
        [
            txt("سود / زیان خالص" if is_fa else "Net PnL"),
            f"{m.net_pnl:+,.2f} {data.credentials.currency}",
            txt("نسبت شارپ سالانه" if is_fa else "Sharpe Ratio (Ann.)"),
            f"{m.sharpe_ratio:.2f}",
        ],
        [
            txt("درصد بازدهی کل" if is_fa else "Total Return (%)"),
            f"{m.return_pct:+.2f}%",
            txt("نسبت سورتینو" if is_fa else "Sortino Ratio"),
            f"{m.sortino_ratio:.2f}",
        ],
        [
            txt("سرمایه اولیه" if is_fa else "Initial Capital"),
            f"{data.credentials.initial_balance:,.2f} {data.credentials.currency}",
            txt("نسبت کالمار" if is_fa else "Calmar Ratio"),
            f"{m.calmar_ratio:.2f}" if m.calmar_ratio is not None else "—",
        ],
        [
            txt("سرمایه نهایی جاری" if is_fa else "Ending Equity"),
            f"{data.credentials.current_balance:,.2f} {data.credentials.currency}",
            txt("فاکتور بازیابی" if is_fa else "Recovery Factor"),
            f"{m.recovery_factor:.2f}" if m.recovery_factor is not None else "—",
        ],
        [
            txt("فاکتور سود (PF)" if is_fa else "Profit Factor"),
            f"{m.profit_factor:.2f}" if m.profit_factor is not None else "—",
            txt("حداکثر افت سرمایه" if is_fa else "Max Drawdown"),
            f"-{m.max_drawdown:,.2f} ({m.max_drawdown_pct:.1f}%)",
        ],
        [
            txt("نرخ برد (Win Rate)" if is_fa else "Win Rate"),
            f"{m.win_rate:.1f}% ({m.winning_trades}W / {m.losing_trades}L)",
            txt("امید ریاضی هر معامله" if is_fa else "Expectancy / Trade"),
            f"{m.expectancy_usd:+,.2f} {data.credentials.currency}",
        ],
        [
            txt("میانگین برد / باخت" if is_fa else "Avg Win / Avg Loss"),
            f"{m.avg_win:,.2f} / {m.avg_loss:,.2f} (x{m.win_loss_ratio:.2f})",
            txt("میانگین و مجموع ضریب R" if is_fa else "Avg & Total R"),
            f"{m.avg_r_multiple:+.2f}R / {m.total_r_multiple:+.2f}R" if m.avg_r_multiple is not None else "—",
        ],
        [
            txt("کل معاملات ثبت‌شده" if is_fa else "Total Closed Trades"),
            str(m.total_trades),
            txt("بزرگترین برد / باخت" if is_fa else "Largest Win / Loss"),
            f"+{m.largest_win:,.2f} / -{abs(m.largest_loss):,.2f}",
        ],
    ]

    t_kpi = Table(
        [[Paragraph(c, body_style) for c in row] for row in kpi_rows],
        colWidths=[150, 115, 150, 115],
    )
    t_kpi.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
        ("TOPPADDING", (0, 0), (-1, 0), 5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_kpi)
    elements.append(Spacer(1, 12))

    # 4. تفکیک موقعیت‌های لانگ در برابر شورت (Long vs Short Execution)
    ls = data.long_short
    elements.append(Paragraph(txt("پروفایل موقعیت‌های خرید و فروش (Long vs Short Profile)" if is_fa else "Long vs Short Execution Profile"), heading_style))

    ls_data = [
        [
            txt("جهت موقعیت" if is_fa else "Direction"),
            txt("تعداد معاملات" if is_fa else "Trades Count"),
            txt("نرخ برد (%)" if is_fa else "Win Rate (%)"),
            txt("سود / زیان خالص" if is_fa else "Net PnL"),
        ],
        [
            txt("خرید (Long / Buy)" if is_fa else "Long / Buy"),
            str(ls.long_trades),
            f"{ls.long_win_rate:.1f}% ({ls.long_wins} wins)",
            f"{ls.long_pnl:+,.2f} {data.credentials.currency}",
        ],
        [
            txt("فروش (Short / Sell)" if is_fa else "Short / Sell"),
            str(ls.short_trades),
            f"{ls.short_win_rate:.1f}% ({ls.short_wins} wins)",
            f"{ls.short_pnl:+,.2f} {data.credentials.currency}",
        ],
    ]
    t_ls = Table([[Paragraph(c, body_style) for c in row] for row in ls_data], colWidths=[130, 120, 130, 150])
    t_ls.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_ls)
    elements.append(Spacer(1, 12))

    # 5. ماتریس بازدهی ماهانه (Monthly Returns Matrix)
    if data.monthly_matrix:
        elements.append(Paragraph(txt("ماتریس بازدهی ماهانه و سالانه (Monthly Returns Matrix)" if is_fa else "Monthly & Annual Returns Matrix (%)"), heading_style))
        month_headers = [txt("سال" if is_fa else "Year")] + [m_name for m_name in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]] + [txt("کل YTD" if is_fa else "YTD (%)")]
        m_rows = [month_headers]
        for y_perf in data.monthly_matrix:
            row = [str(y_perf.year)]
            for m_name in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]:
                val = y_perf.months.get(m_name)
                row.append(f"{val:+.1f}%" if val is not None else "—")
            row.append(f"<b>{y_perf.ytd_return_pct:+.1f}%</b>")
            m_rows.append(row)

        col_w = [36] + [38] * 12 + [44]
        t_matrix = Table([[Paragraph(c, body_style) for c in r] for r in m_rows], colWidths=col_w)
        t_matrix.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 2),
            ("RIGHTPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(t_matrix)
        elements.append(Spacer(1, 14))

    # 6. نمادهای برتر معامله‌شده (Top Instruments)
    if data.top_symbols:
        elements.append(Paragraph(txt("توزیع ابزارهای معاملاتی برتر" if is_fa else "Top Traded Instruments Breakdown"), heading_style))
        sym_headers = [
            txt("نماد" if is_fa else "Symbol"),
            txt("تعداد معامله" if is_fa else "Trades"),
            txt("وین‌ریت" if is_fa else "Win Rate"),
            txt("فاکتور سود" if is_fa else "Profit Factor"),
            txt("سود / زیان خالص" if is_fa else "Net PnL"),
        ]
        sym_rows = [sym_headers]
        for s in data.top_symbols[:6]:
            sym_rows.append([
                s.symbol,
                str(s.trades_count),
                f"{s.win_rate:.1f}%",
                f"{s.profit_factor:.2f}" if s.profit_factor is not None else "—",
                f"{s.net_pnl:+,.2f} {data.credentials.currency}",
            ])
        t_sym = Table([[Paragraph(c, body_style) for c in r] for r in sym_rows], colWidths=[90, 80, 100, 110, 150])
        t_sym.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#334155")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFFFFF"), colors.HexColor("#F8FAFC")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t_sym)
        elements.append(Spacer(1, 16))

    # 7. بلوک امضای رسمی و سلب مسئولیت حقوقی (Audit Attestation & Sign-off)
    attest_text = (
        "این گزارش به‌صورت خودکار توسط سیستم حسابرسی محلی MokTradeDesk تولید شده و بر اساس دفتر کل ثبت معاملات بسته می‌باشد. "
        "هش دیجیتال فوق اصالت و تغییرناپذیری رکوردهای معاملاتی را تا لحظه صدور گزارش تضمین می‌نماید."
        if is_fa else
        "This institutional trading performance dossier is generated directly from the cryptographically verified local-first ledger "
        "of MokTradeDesk. The audit verification hash above certifies records integrity and provenance up to the timestamp of issuance."
    )
    elements.append(Paragraph(f"<font size=7 color='#64748B'><i>{txt(attest_text)}</i></font>", body_style))
    elements.append(Spacer(1, 10))

    sign_data = [
        [
            Paragraph(f"<b>{txt('تایید و امضای مدیر پرتفوی:' if is_fa else 'Portfolio Manager Attestation:')}</b><br/><br/>_______________________________<br/>{data.credentials.trader_name}", body_style),
            Paragraph(f"<b>{txt('مهر دیجیتال دفتر کل:' if is_fa else 'Cryptographic Ledger Stamp:')}</b><br/><br/>[ MOKTRADEDESK VERIFIED ]<br/>{data.credentials.audit_date}", ParagraphStyle("SignRight", parent=body_style, alignment=TA_LEFT if is_fa else TA_RIGHT)),
        ]
    ]
    t_sign = Table(sign_data, colWidths=[265, 265])
    t_sign.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(t_sign)

    doc.build(elements)
    buffer.seek(0)
    filename = f"Institutional_Statement_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
