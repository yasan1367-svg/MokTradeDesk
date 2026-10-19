"""Authoritative request/response contracts for Strategy and version APIs."""
from datetime import datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from ..models.strategy import StrategyStatus


def _clean_label(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("نام نمی‌تواند خالی باشد")
    return value


def _normalize_test_type(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    value = value.strip().lower()
    if value not in {"backtest", "forward", "real", "real_personal", "real_prop"}:
        raise ValueError("نوع نسخه نامعتبر است")
    return value


def _normalize_status(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    value = value.strip().lower()
    if value not in {item.value for item in StrategyStatus}:
        raise ValueError("وضعیت نسخه نامعتبر است")
    return value


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        return _clean_label(value)


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_blank(cls, value):
        return _clean_label(value) if value is not None else value


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str]
    created_at: datetime


class StrategyListResponse(StrategyResponse):
    versions_count: int


class VersionCreate(BaseModel):
    version_name: str
    rules_note: Optional[str] = None
    test_type: Optional[str] = None
    status: Optional[str] = None

    @field_validator("version_name")
    @classmethod
    def label_not_blank(cls, value):
        return _clean_label(value)

    @field_validator("test_type")
    @classmethod
    def valid_version_label_type(cls, value):
        return _normalize_test_type(value)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        return _normalize_status(value)


class VersionUpdate(BaseModel):
    version_name: Optional[str] = None
    rules_note: Optional[str] = None
    test_type: Optional[str] = None
    status: Optional[str] = None

    @field_validator("version_name")
    @classmethod
    def label_not_blank(cls, value):
        return _clean_label(value) if value is not None else value

    @field_validator("test_type")
    @classmethod
    def valid_version_label_type(cls, value):
        return _normalize_test_type(value)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        return _normalize_status(value)


class ForkRequest(BaseModel):
    version_name: Optional[str] = None
    rules_note: Optional[str] = None
    test_type: Optional[str] = None
    status: Optional[str] = None

    @field_validator("version_name")
    @classmethod
    def label_not_blank(cls, value):
        return _clean_label(value) if value is not None else value

    @field_validator("test_type")
    @classmethod
    def valid_version_label_type(cls, value):
        return _normalize_test_type(value)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value):
        return _normalize_status(value)


class VersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    strategy_id: int
    version_name: str
    rules_note: Optional[str]
    status: str
    test_type: Optional[str] = None
    forked_from_version_id: Optional[int] = None
    trades_count: int = 0
    trade_counts_by_test_type: dict[str, int] = {}
    strategy_name: Optional[str] = None
    created_at: datetime


class StrategyStatsResponse(BaseModel):
    """Stable envelope for existing strategy stats (metric payload remains extensible)."""
    strategy_id: int
    strategy_name: str
    total_trades: int
    summary: dict[str, Any]
    trade_counts: dict[str, Any]