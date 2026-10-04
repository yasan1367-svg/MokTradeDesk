"""Migrate page colors to CSS variables."""
import re, os

FILES = {
    "Sidebar.tsx": r"c:\MokTradeDesk\frontend\src\components\Sidebar.tsx",
    "DashboardPage.tsx": r"c:\MokTradeDesk\frontend\src\pages\DashboardPage.tsx",
    "TradesPage.tsx": r"c:\MokTradeDesk\frontend\src\pages\TradesPage.tsx",
    "PropPage.tsx": r"c:\MokTradeDesk\frontend\src\pages\PropPage.tsx",
}

# (old, new) — ordered by specificity
REPLACEMENTS = [
    # Backgrounds
    ("bg-white", "bg-[var(--bg-card)]"),
    ("bg-[#FFFFFF]", "bg-[var(--bg-card)]"),
    ("bg-[#EEF2F9]", "bg-[var(--bg-base)]"),
    ("bg-[#0F1923]", "bg-[var(--bg-base)]"),
    ("bg-[#152238]", "bg-[var(--bg-sidebar)]"),
    ("bg-[#1A2736]", "bg-[var(--bg-card)]"),
    ("bg-[#1E2F41]", "bg-[var(--bg-input)]"),
    ("bg-[#1E2F4D]", "bg-[var(--bg-sidebar-hover)]"),
    ("bg-[#243447]", "bg-[var(--bg-elevated)]"),
    ("bg-[#2A3F5E]", "bg-[var(--border-medium)]"),
    ("bg-[#F5F7FB]", "bg-[var(--bg-elevated)]"),
    ("bg-[#F8FAFF]", "bg-[var(--bg-input)]"),
    ("bg-[#F1F4F9]", "bg-[var(--bg-elevated)]"),
    ("bg-[#3F7CFF]", "bg-[var(--accent)]"),
    ("bg-[#13AE81]", "bg-[var(--profit)]"),
    ("bg-[#E45D72]", "bg-[var(--loss)]"),
    ("bg-[#D99B25]", "bg-[var(--warning)]"),
    ("bg-[#7959D6]", "bg-[var(--purple)]"),
    ("bg-[#EDF3FF]", "bg-[var(--accent-soft)]"),
    ("bg-[#E5F8F1]", "bg-[var(--profit-soft)]"),
    ("bg-[#FFEDF0]", "bg-[var(--loss-soft)]"),
    ("bg-[#FFF5DB]", "bg-[var(--warning-soft)]"),
    # Text
    ("text-[#1A2B47]", "text-[var(--text-primary)]"),
    ("text-[#E0E8F0]", "text-[var(--text-primary)]"),
    ("text-[#B9C8DE]", "text-[var(--sidebar-text)]"),
    ("text-[#6B7A94]", "text-[var(--text-secondary)]"),
    ("text-[#7A8488]", "text-[var(--text-secondary)]"),
    ("text-[#8DA2C1]", "text-[var(--sidebar-text-muted)]"),
    ("text-[#9AA8BF]", "text-[var(--text-muted)]"),
    ("text-[#4A5256]", "text-[var(--text-muted)]"),
    ("text-[#3563BE]", "text-[var(--accent-strong)]"),
    ("text-[#5A7290]", "text-[var(--text-muted)]"),
    # Borders
    ("border-[#E5EBF3]", "border-[var(--border-subtle)]"),
    ("border-[#D5DDE8]", "border-[var(--border-medium)]"),
    ("border-[#2A3F5E]", "border-[var(--border-medium)]"),
    ("border-[#2A3E54]", "border-[var(--border-subtle)]"),
    ("border-[#A9C1FA]", "border-[var(--border-accent)]"),
    # Hex in inline styles (template literals)
    ("#3F7CFF", "var(--accent)"),
    ("#5B8DEF", "var(--accent-strong)"),
    ("#76A4FF", "var(--accent)"),
    ("#2563EB", "var(--accent-strong)"),
    ("#DCE8FF", "var(--accent-light)"),
    ("#C5D9FF", "var(--accent-light)"),
    ("#A9C1FA", "var(--border-accent)"),
    ("#13AE81", "var(--profit)"),
    ("#4DD9A9", "var(--profit-border)"),
    ("#A8E6CF", "var(--profit-border)"),
    ("#E45D72", "var(--loss)"),
    ("#F0A6B2", "var(--loss-border)"),
    ("#D99B25", "var(--warning)"),
    ("#F0BE5C", "var(--warning-border)"),
    ("#7959D6", "var(--purple)"),
    ("#152238", "var(--bg-sidebar)"),
    ("#1A2736", "var(--bg-card)"),
    ("#0F1923", "var(--bg-base)"),
    ("#E0E8F0", "var(--text-primary)"),
    ("#1A2B47", "var(--text-primary)"),
    ("#6B7A94", "var(--text-secondary)"),
    ("#9AA8BF", "var(--text-muted)"),
    ("#E5EBF3", "var(--border-subtle)"),
    ("#D5DDE8", "var(--border-medium)"),
    ("#2A3E54", "var(--border-subtle)"),
    ("#EDF3FF", "var(--accent-soft)"),
    ("#E5F8F1", "var(--profit-soft)"),
    ("#FFEDF0", "var(--loss-soft)"),
]

def count_hex(text):
    return len(re.findall(r'#[0-9A-Fa-f]{6}', text))

for name, path in FILES.items():
    with open(path) as f:
        content = f.read()
    before = count_hex(content)
    for old, new in REPLACEMENTS:
        # Only replace when pattern is NOT already in a var() context
        content = re.sub(
            re.escape(old) + r'(?!\s*\))',
            lambda m: new if 'var(' not in content[max(0,m.start()-5):m.start()] else m.group(0),
            content
        )
    after = count_hex(content)
    with open(path, 'w') as f:
        f.write(content)
    print(f"{name}: {before} hex -> {after} hex ({before-after} replaced)")
    if after > 0:
        remain = re.findall(r'#[0-9A-Fa-f]{6}', content)
        for h in sorted(set(remain), key=lambda x: -remain.count(x)):
            print(f"  LEFT: {h} (x{remain.count(h)})")