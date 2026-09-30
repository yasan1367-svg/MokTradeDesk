import io
import os

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from ..services import metrics

# ═════════════════════════════════════════════
# Font Registration — Vazirmatn
# ═════════════════════════════════════════════
FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
VAZIR_REGULAR = os.path.join(FONTS_DIR, "Vazirmatn-Regular.ttf")
VAZIR_BOLD = os.path.join(FONTS_DIR, "Vazirmatn-Bold.ttf")

if os.path.exists(VAZIR_REGULAR):
    fm.fontManager.addfont(VAZIR_REGULAR)
    fm.fontManager.addfont(VAZIR_BOLD)
    _FONT_NAME = "Vazirmatn"
else:
    _FONT_NAME = "DejaVu Sans"

plt.rcParams["font.family"] = _FONT_NAME
plt.rcParams["axes.unicode_minus"] = False


def get_font_path(style="regular"):
    if style == "bold":
        return VAZIR_BOLD
    return VAZIR_REGULAR


# ═════════════════════════════════════════════
# Chart: Equity Curve
# ═════════════════════════════════════════════
def draw_equity_chart(trades) -> io.BytesIO:
    """نمودار Equity Curve از لیست معاملات"""
    closed = [t for t in trades if t.close_time is not None]
    sorted_trades = sorted(closed, key=lambda t: t.close_time)

    equity = []
    cum = 0.0
    for t in sorted_trades:
        cum += metrics.net_pnl(t)
        equity.append(cum)

    if not equity:
        equity = [0]

    fig, ax = plt.subplots(figsize=(7, 2.5))
    ax.fill_between(range(len(equity)), equity, alpha=0.15, color="#3F7CFF")
    ax.plot(equity, color="#3F7CFF", linewidth=2)
    ax.axhline(y=0, color="#D0D5DD", linewidth=0.8, linestyle="--")
    ax.set_xlim(0, len(equity) - 1 if len(equity) > 1 else 1)
    ax.set_ylabel("Equity ($)", fontsize=9)
    ax.set_xlabel("Trade #", fontsize=9)
    ax.tick_params(labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # fill green/red
    if len(equity) > 1:
        final = equity[-1]
        color = "#13AE81" if final >= 0 else "#E45D72"
        ax.plot(len(equity) - 1, final, "o", color=color, markersize=6)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return buf


# ═════════════════════════════════════════════
# Chart: Win / Loss Pie
# ═════════════════════════════════════════════
def draw_win_loss_pie(trades) -> io.BytesIO:
    """نمودار دایره‌ای نسبت برد به باخت"""
    closed = [t for t in trades if t.close_time is not None]
    wins = sum(1 for t in closed if metrics.net_pnl(t) > 0)
    losses = sum(1 for t in closed if metrics.net_pnl(t) < 0)
    neutral = len(closed) - wins - losses

    labels = []
    sizes = []
    colors = []
    if wins > 0:
        labels.append(f"Wins ({wins})")
        sizes.append(wins)
        colors.append("#13AE81")
    if losses > 0:
        labels.append(f"Losses ({losses})")
        sizes.append(losses)
        colors.append("#E45D72")
    if neutral > 0:
        labels.append(f"Neutral ({neutral})")
        sizes.append(neutral)
        colors.append("#9AA8BF")

    if not sizes:
        sizes = [1]
        labels = ["No data"]
        colors = ["#D0D5DD"]

    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct="%1.0f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 9},
        pctdistance=0.75,
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_color("white")
        at.set_fontweight("bold")

    ax.axis("equal")
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    buf.seek(0)
    return buf