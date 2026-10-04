from datetime import datetime
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

from ..models.strategy import TradeSource, TestType
from ..utils.import_identity import compute_trade_hash
from ..utils.trade_metrics import calculate_r_multiple


# ═════════════════════════════════════════════
# Helpers
# ═════════════════════════════════════════════
# فاز ۳۰: منطق hash در `utils/import_identity.py` متمرکز شد (همان فرمول قبلی).
# نام قدیمی برای سازگاری حفظ شده است.
_calculate_trade_hash = compute_trade_hash


# ═════════════════════════════════════════════
# Soft4X Importer
# ═════════════════════════════════════════════
class Soft4XImporter:
    """واردکننده فایل‌های اکسل خروجی Soft4X"""

    def __init__(self, db: Session, symbol: str = "XAUUSD", test_type: str = "backtest"):
        self.db = db
        self.symbol = symbol
        self.test_type = TestType(test_type)

    def parse_file(
        self,
        file_path: str,
        column_mapping: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Parse XLSX (فاز ۳۰: پشتیبانی از Column Mapping پروفایل ایمپورت).

        `column_mapping` نگاشتِ «فیلد کانونیکال → نام هدر یا ایندکس صفر-مبنا» است
        و هدرهای پیش‌فرض را بازنویسی می‌کند؛ مثلاً `{"open_time": "Time Open", "pnl": 8}`.
        """
        from openpyxl import load_workbook

        wb = load_workbook(file_path, data_only=True)
        ws = wb["Trades"] if "Trades" in wb.sheetnames else wb.active

        headers = []
        for cell in ws[1]:
            headers.append(cell.value)

        col_index = {}
        for idx, header in enumerate(headers):
            if header:
                col_index[str(header).strip()] = idx

        def column(field: str, default_header: str) -> Optional[int]:
            """ایندکس ستون: اول نگاشت کاربر، بعد هدر پیش‌فرض."""
            target = (column_mapping or {}).get(field)
            if isinstance(target, int):
                return target
            if target is not None:
                mapped = col_index.get(str(target).strip())
                if mapped is not None:
                    return mapped
            return col_index.get(default_header)

        open_time_col = column("open_time", "Open Time")

        trades = []
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or row[0] is None:
                continue

            if open_time_col is None:
                continue

            open_time = self._to_datetime(self._get_value(row, open_time_col))
            close_time = self._to_datetime(
                self._get_value(row, column("close_time", "Close Time"))
            )

            if open_time is None:
                continue

            direction = self._get_direction(self._get_value(row, column("type", "Type")))
            if direction is None:
                continue

            open_price = float(
                self._get_value(row, column("open_price", "Open Price"), 0) or 0
            )
            close_price = float(
                self._get_value(row, column("close_price", "Close Price"), 0) or 0
            )
            sl = self._to_float(self._get_value(row, column("sl", "SL")))
            # فاز ۵۳.۳: استاپِ اولیه (Soft4X) — مبنای درست R (حتی اگر SL جابجا شده باشد)
            initial_sl = self._to_float(
                self._get_value(row, column("initial_sl", "Initial SL"))
            )

            raw_data = self._make_json_safe({
                headers[i]: row[i] for i in range(len(row)) if i < len(headers)
            })
            if initial_sl is not None:
                raw_data["initial_sl"] = initial_sl

            trade = {
                "symbol": self.symbol,
                "test_type": self.test_type,
                "direction": direction,
                "open_time": open_time,
                "close_time": close_time,
                "open_price": open_price,
                "close_price": close_price,
                "size": float(self._get_value(row, column("size", "Size"), 0) or 0),
                "sl": sl,
                "initial_sl": initial_sl,
                "tp": self._to_float(self._get_value(row, column("tp", "TP"))),
                "pnl": float(self._get_value(row, column("pnl", "P/L"), 0) or 0),
                "r_multiple": calculate_r_multiple(direction, open_price, close_price, sl, initial_sl),
                "commission": self._to_float(
                    self._get_value(row, column("commission", "Commission"))
                ) or 0,
                "swap": 0.0,
                "entry_sequence": 1,
                "source": TradeSource.SOFT4X_IMPORT,
                "raw_data": raw_data,
            }
            trades.append(trade)

        return trades

    def _apply_symbol_mapping(self, symbol: str) -> str:
        from ..models.strategy import SymbolMapping
        mapping = self.db.query(SymbolMapping).filter(
            SymbolMapping.original_symbol == symbol
        ).first()
        if mapping:
            return mapping.canonical_symbol
        return symbol

    def _get_value(self, row, index, default=None):
        if index is None:
            return default
        try:
            value = row[index] if index < len(row) else default
            return value if value is not None else default
        except:
            return default

    def _get_direction(self, value):
        if value is None:
            return None
        normalized = str(value).strip().lower()
        if normalized == "buy":
            return "buy"
        if normalized == "sell":
            return "sell"
        return None

    def _to_float(self, value):
        if value is None:
            return None
        try:
            return float(value)
        except:
            return None

    def _to_datetime(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            if hasattr(value, 'to_pydatetime'):
                return value.to_pydatetime()
            return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S")
        except:
            try:
                return datetime.fromisoformat(str(value))
            except:
                return None

    def _make_json_safe(self, data: dict) -> dict:
        safe_data = {}
        for key, value in data.items():
            if value is None:
                safe_data[key] = None
            elif isinstance(value, datetime):
                safe_data[key] = value.isoformat()
            elif hasattr(value, 'to_pydatetime'):
                safe_data[key] = value.to_pydatetime().isoformat()
            elif hasattr(value, 'isoformat'):
                safe_data[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool)):
                safe_data[key] = value
            else:
                safe_data[key] = str(value)
        return safe_data


# ═════════════════════════════════════════════
# MT4 Importer
# ═════════════════════════════════════════════
class MT4Importer:
    """واردکننده فایل‌های HTML متاتریدر — Positions + Orders برای initial_sl."""

    def __init__(self, db: Session, test_type: str = "backtest"):
        self.db = db
        self.test_type = TestType(test_type)
        self._order_sl_map: Dict[str, float] = {}

    def _parse_orders(self, rows: list, start_idx: int, end_idx: int) -> Dict[str, float]:
        """Build ticket -> order_sl map from Orders section.

        Orders rows considered: with State == 'filled'.
        Columns (0-based): 0=Time, 1=Position, 2=Symbol, 3=Type,
                           4=Volume, 5=Price, 6=S/L, 7=T/P, 8=State, ...
        """
        order_map: Dict[str, float] = {}
        for i in range(start_idx, end_idx):
            row = rows[i]
            cells = row.find_all('td')
            visible = [c for c in cells if 'hidden' not in (c.get('class') or [])]
            if len(visible) < 9:
                continue
            state = visible[8].get_text(strip=True).lower()
            if state != "filled":
                continue
            position = visible[1].get_text(strip=True)
            try:
                order_sl = float(visible[6].get_text(strip=True).replace(',', ''))
                order_map[position] = order_sl
            except (ValueError, IndexError):
                continue
        return order_map

    def parse_html(self, html_content: str) -> List[Dict[str, Any]]:
        soup = BeautifulSoup(html_content, 'html.parser')
        trades = []
        rows = soup.find_all('tr')

        section_markers = []
        for idx, row in enumerate(rows):
            row_text = row.get_text(strip=True)
            if 'Positions' in row_text and row.find('th'):
                section_markers.append(('positions', idx))
                continue
            if ('Orders' in row_text or 'Deals' in row_text) and row.find('th'):
                section_markers.append(('orders', idx))
                continue

        # Parse Orders first (to build initial_sl map)
        self._order_sl_map = {}
        for i, (stype, sidx) in enumerate(section_markers):
            if stype == 'orders':
                start = sidx + 2  # skip header row
                if i + 1 < len(section_markers):
                    end = section_markers[i + 1][1]
                else:
                    end = len(rows)
                self._order_sl_map = self._parse_orders(rows, start, end)
                break

        # Parse Positions
        in_positions_section = False
        header_skipped = False

        for idx, row in enumerate(rows):
            row_text = row.get_text(strip=True)

            if 'Positions' in row_text and row.find('th'):
                in_positions_section = True
                header_skipped = False
                continue

            if ('Orders' in row_text or 'Deals' in row_text) and row.find('th'):
                in_positions_section = False
                continue

            if not in_positions_section:
                continue

            if not header_skipped:
                header_skipped = True
                continue

            all_cells = row.find_all('td')
            visible_cells = [
                c for c in all_cells
                if 'hidden' not in (c.get('class') or [])
            ]

            if len(visible_cells) >= 13:
                try:
                    trade = self._parse_row(visible_cells)
                    if trade:
                        trades.append(trade)
                except Exception as e:
                    print(f"  ❌ خطا: {e}")

        return trades

    def _parse_row(self, cells) -> Optional[Dict[str, Any]]:
        try:
            open_time = self._to_datetime(cells[0].get_text(strip=True))
            position = cells[1].get_text(strip=True)
            symbol = cells[2].get_text(strip=True)
            direction_raw = cells[3].get_text(strip=True).lower()
            volume = float(cells[4].get_text(strip=True))
            open_price = float(cells[5].get_text(strip=True).replace(',', ''))
            sl = self._to_float(cells[6].get_text(strip=True))
            tp = self._to_float(cells[7].get_text(strip=True))
            close_time = self._to_datetime(cells[8].get_text(strip=True))
            close_price = self._to_float(cells[9].get_text(strip=True))
            commission = self._to_float(cells[10].get_text(strip=True)) or 0
            swap = self._to_float(cells[11].get_text(strip=True)) or 0
            profit = self._to_float(cells[12].get_text(strip=True)) or 0

            if open_time is None:
                return None

            if "buy" in direction_raw:
                direction = "buy"
            elif "sell" in direction_raw:
                direction = "sell"
            else:
                return None

            # فاز ۴: استاپ اولیه از Orders (اگر یافت نشد -> fallback به SL Positions)
            initial_sl = self._order_sl_map.get(position, sl)

            return {
                "symbol": self._apply_symbol_mapping(symbol),
                "test_type": self.test_type,
                "direction": direction,
                "open_time": open_time,
                "close_time": close_time,
                "open_price": open_price,
                "close_price": close_price,
                "size": volume,
                "sl": sl,
                "initial_sl": initial_sl,
                "tp": tp,
                "pnl": profit,
                "r_multiple": calculate_r_multiple(direction, open_price, close_price, sl, initial_sl),
                "commission": commission,
                "swap": swap,
                "entry_sequence": 1,
                "source": TradeSource.MT4_IMPORT,
                "raw_data": {
                    "position": position,
                    "raw_direction": direction_raw,
                },
            }
        except Exception as e:
            print(f"  ❌ خطای _parse_row: {e}")
            return None

    def _apply_symbol_mapping(self, symbol: str) -> str:
        from ..models.strategy import SymbolMapping
        mapping = self.db.query(SymbolMapping).filter(
            SymbolMapping.original_symbol == symbol
        ).first()
        if mapping:
            return mapping.canonical_symbol
        return symbol

    def _to_float(self, value: str) -> Optional[float]:
        if not value or value in ['', '-', 'N/A']:
            return None
        try:
            return float(value.replace(',', '').replace(' ', ''))
        except:
            return None

    def _to_datetime(self, value: str) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.strptime(value.strip(), "%Y.%m.%d %H:%M:%S")
        except:
            try:
                return datetime.strptime(value.strip(), "%Y.%m.%d %H:%M")
            except:
                return None