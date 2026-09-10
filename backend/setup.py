# make_frontend_structure.py
import os

files = {
    "src/stores/useStrategyStore.ts": "// کد useStrategyStore.ts را قرار دهید\n",
    "src/stores/usePropStore.ts": "// کد usePropStore.ts را قرار دهید\n",
    "src/stores/useLedgerStore.ts": "// کد useLedgerStore.ts را قرار دهید\n",
    "src/components/Dashboard.tsx": "// کد Dashboard.tsx را قرار دهید\n",
    "src/components/StrategyLab.tsx": "// کد StrategyLab.tsx را قرار دهید\n",
    "src/components/PropDesk.tsx": "// کد PropDesk.tsx را قرار دهید\n",
    "src/components/JournalLedger.tsx": "// کد JournalLedger.tsx را قرار دهید\n",
    "src/components/ImportModal.tsx": "// کد ImportModal.tsx را قرار دهید\n",
}

for path, content in files.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Created: {path}")
    else:
        print(f"Skipped (Already exists): {path}")

print("\n ساختار فایل‌ها و پوشه‌های فرانت‌اند با موفقیت ایجاد شد.")