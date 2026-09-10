import io
import csv
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
import pandas as pd
from bs4 import BeautifulSoup


class TradeImportRecord(BaseModel):
    ticket: str
    symbol: str
    order_type: str  # BUY / SELL
    lots: float
    open_time: datetime
    close_time: Optional[datetime] = None
    open_price: float
    close_price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    commission: float = 0.0
    swap: float = 0.0
    profit: float = 0.0
    pips: float = 0.0
    comment: Optional[str] = None


class ImportResult(BaseModel):
    success: bool
    total_records: int
    imported_count: int
    failed_count: int
    trades: List[TradeImportRecord]
    errors: List[str]


class ImportService:
    @staticmethod
    def parse_datetime(date_str: Any) -> Optional[datetime]:
        if not date_str or pd.isna(date_str):
            return None
        
        if isinstance(date_str, datetime):
            return date_str

        date_str = str(date_str).strip()
        formats = [
            "%Y.%m.%d %H:%M:%S",
            "%Y.%m.%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y %H:%M",
            "%Y/%m/%d %H:%M:%S",
            "%Y/%m/%d %H:%M",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None

    @classmethod
    def parse_mt4_mt5_html(cls, content: str) -> List[TradeImportRecord]:
        soup = BeautifulSoup(content, "html.parser")
        rows = soup.find_all("tr")
        trades: List[TradeImportRecord] = []

        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
            if not cols:
                continue

            if len(cols) >= 13 and cols[0].isdigit():
                try:
                    ticket = cols[0]
                    open_time = cls.parse_datetime(cols[1])
                    order_type = cols[2].upper()
                    lots = float(cols[3])
                    symbol = cols[4]
                    open_price = float(cols[5])
                    sl = float(cols[6]) if cols[6] != "0" else None
                    tp = float(cols[7]) if cols[7] != "0" else None
                    
                    close_time: Optional[datetime] = cls.parse_datetime(cols[8])
                    close_price: Optional[float] = float(cols[9]) if cols[9] else None
                    
                    commission = float(cols[10]) if len(cols) > 10 else 0.0
                    swap = float(cols[11]) if len(cols) > 11 else 0.0
                    profit = float(cols[12]) if len(cols) > 12 else 0.0

                    if open_time:
                        trades.append(
                            TradeImportRecord(
                                ticket=ticket,
                                symbol=symbol,
                                order_type=order_type,
                                lots=lots,
                                open_time=open_time,
                                close_time=close_time,
                                open_price=open_price,
                                close_price=close_price,
                                sl=sl,
                                tp=tp,
                                commission=commission,
                                swap=swap,
                                profit=profit
                            )
                        )
                except Exception:
                    continue

        return trades

    @classmethod
    def parse_ctrader_csv(cls, df: pd.DataFrame) -> List[TradeImportRecord]:
        trades: List[TradeImportRecord] = []

        for _, row in df.iterrows():
            try:
                ticket = str(row.get("Position ID", row.get("Id", "")))
                symbol = str(row.get("Symbol", ""))
                order_type = str(row.get("Entry Type", row.get("Type", ""))).upper()
                lots = float(row.get("Volume", row.get("Quantity", 0)))
                
                open_time_str = row.get("Entry Time", row.get("Open Time", None))
                open_time = cls.parse_datetime(open_time_str)

                close_time: Optional[datetime] = None
                close_time_str = row.get("Closing Time", row.get("Close Time", None))
                if close_time_str:
                    close_time = cls.parse_datetime(close_time_str)

                open_price = float(row.get("Entry Price", row.get("Open Price", 0)))
                close_price_raw = row.get("Closing Price", row.get("Close Price", None))
                close_price: Optional[float] = float(close_price_raw) if close_price_raw and not pd.isna(close_price_raw) else None

                profit = float(row.get("Net Profit", row.get("Profit", 0)))
                commission = float(row.get("Commissions", row.get("Commission", 0)))
                swap = float(row.get("Swaps", row.get("Swap", 0)))

                if open_time and symbol:
                    trades.append(
                        TradeImportRecord(
                            ticket=ticket,
                            symbol=symbol,
                            order_type=order_type,
                            lots=lots,
                            open_time=open_time,
                            close_time=close_time,
                            open_price=open_price,
                            close_price=close_price,
                            profit=profit,
                            commission=commission,
                            swap=swap
                        )
                    )
            except Exception:
                continue

        return trades

    @classmethod
    def parse_generic_df(cls, df: pd.DataFrame) -> List[TradeImportRecord]:
        trades: List[TradeImportRecord] = []
        
        # یکسان‌سازی نام ستون‌ها
        df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]

        for index, row in df.iterrows():
            try:
                ticket = str(row.get("ticket", row.get("id", index + 1)))
                symbol = str(row.get("symbol", row.get("item", "UNKNOWN")))
                order_type = str(row.get("type", row.get("cmd", "BUY"))).upper()
                lots = float(row.get("lots", row.get("size", row.get("volume", 0.01))))
                
                open_time_val = row.get("open_time", row.get("opentime", row.get("time", None)))
                open_time = cls.parse_datetime(open_time_val)

                # تعریف صریح متغیر close_time قبل از هرگونه پردازش جهت جلوگیری از خطای Pylance
                close_time: Optional[datetime] = None
                close_time_val = row.get("close_time", row.get("closetime", None))
                if close_time_val is not None and not pd.isna(close_time_val):
                    close_time = cls.parse_datetime(close_time_val)

                open_price = float(row.get("open_price", row.get("openprice", row.get("price", 0.0))))
                
                close_price: Optional[float] = None
                close_price_val = row.get("close_price", row.get("closeprice", None))
                if close_price_val is not None and not pd.isna(close_price_val):
                    close_price = float(close_price_val)

                sl = float(row.get("sl", 0.0)) or None
                tp = float(row.get("tp", 0.0)) or None
                commission = float(row.get("commission", 0.0))
                swap = float(row.get("swap", 0.0))
                profit = float(row.get("profit", row.get("pnl", 0.0)))
                comment = str(row.get("comment", "")) if row.get("comment") else None

                if open_time:
                    trades.append(
                        TradeImportRecord(
                            ticket=ticket,
                            symbol=symbol,
                            order_type=order_type,
                            lots=lots,
                            open_time=open_time,
                            close_time=close_time,
                            open_price=open_price,
                            close_price=close_price,
                            sl=sl,
                            tp=tp,
                            commission=commission,
                            swap=swap,
                            profit=profit,
                            comment=comment
                        )
                    )
            except Exception:
                continue

        return trades

    @classmethod
    def process_file_import(cls, file_bytes: bytes, filename: str) -> ImportResult:
        errors: List[str] = []
        trades: List[TradeImportRecord] = []

        try:
            ext = filename.split(".")[-1].lower() if "." in filename else ""

            if ext in ["html", "htm"]:
                content = file_bytes.decode("utf-8", errors="ignore")
                trades = cls.parse_mt4_mt5_html(content)
            elif ext in ["csv", "txt"]:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes))
                except Exception:
                    df = pd.read_csv(io.BytesIO(file_bytes), sep=";")
                
                if "Position ID" in df.columns or "Entry Time" in df.columns:
                    trades = cls.parse_ctrader_csv(df)
                else:
                    trades = cls.parse_generic_df(df)
            elif ext in ["xlsx", "xls"]:
                df = pd.read_excel(io.BytesIO(file_bytes))
                trades = cls.parse_generic_df(df)
            else:
                errors.append("فرمت فایل پشتیبانی نمی‌شود. لطفاً فایل CSV، Excel یا HTML انتخاب کنید.")

        except Exception as e:
            errors.append(f"خطا در پردازش فایل: {str(e)}")

        return ImportResult(
            success=len(trades) > 0 and len(errors) == 0,
            total_records=len(trades),
            imported_count=len(trades),
            failed_count=len(errors),
            trades=trades,
            errors=errors
        )