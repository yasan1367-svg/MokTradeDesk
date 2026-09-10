from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class PropStageType(str, Enum):
    STAGE_1 = "Stage 1"
    STAGE_2 = "Stage 2"
    FUNDED = "Funded"


class AccountStatus(str, Enum):
    ACTIVE = "Active"
    PASSED = "Passed"
    FAILED = "Failed"
    CLOSED = "Closed"


class PropFirmRules(BaseModel):
    max_daily_dd_pct: float = Field(..., description="حداکثر دراودان روزانه مجاز به درصد")
    max_total_dd_pct: float = Field(..., description="حداکثر دراودان کل مجاز به درصد")
    target_stage_1_pct: float = Field(..., description="تارگت سود مرحله اول به درصد")
    target_stage_2_pct: float = Field(..., description="تارگت سود مرحله دوم به درصد")
    profit_split_pct: float = Field(default=80.0, description="سهم سود معامله‌گر در حساب اصلی")


class PropFirm(BaseModel):
    id: int
    name: str
    rules: PropFirmRules


class PropStage(BaseModel):
    id: int
    account_id: int
    stage_type: PropStageType
    initial_balance: float
    current_balance: float
    equity: float
    profit_target: Optional[float]
    max_daily_loss_limit: float
    max_total_loss_limit: float
    status: AccountStatus = AccountStatus.ACTIVE
    failure_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    passed_at: Optional[datetime] = None


class PropWithdrawal(BaseModel):
    id: int
    account_id: int
    amount: float
    trader_share_amount: float
    withdrawal_date: datetime = Field(default_factory=datetime.utcnow)
    status: str = "Completed"


class PropAccount(BaseModel):
    id: int
    firm_id: int
    account_number: str
    account_size: float
    current_stage_type: PropStageType
    status: AccountStatus = AccountStatus.ACTIVE
    current_profit: float = 0.0
    total_withdrawn: float = 0.0


class PropService:
    # دیتابیس درخافظه موقت (برای تست و توسعه)
    firms_db: Dict[int, PropFirm] = {}
    accounts_db: Dict[int, PropAccount] = {}
    stages_db: Dict[int, PropStage] = {}
    withdrawals_db: List[PropWithdrawal] = []

    _firm_id_counter = 1
    _account_id_counter = 1
    _stage_id_counter = 1
    _withdrawal_id_counter = 1

    @classmethod
    def create_firm(cls, name: str, rules: PropFirmRules) -> PropFirm:
        firm = PropFirm(id=cls._firm_id_counter, name=name, rules=rules)
        cls.firms_db[firm.id] = firm
        cls._firm_id_counter += 1
        return firm

    @classmethod
    def create_account(cls, firm_id: int, account_number: str, account_size: float) -> PropAccount:
        firm = cls.firms_db.get(firm_id)
        if not firm:
            raise ValueError(f"Prop firm with id {firm_id} not found.")

        account = PropAccount(
            id=cls._account_id_counter,
            firm_id=firm_id,
            account_number=account_number,
            account_size=account_size,
            current_stage_type=PropStageType.STAGE_1,
            status=AccountStatus.ACTIVE,
        )
        cls.accounts_db[account.id] = account
        cls._account_id_counter += 1

        # ایجاد خودکار Stage 1 بر اساس قوانین شرکت
        cls._create_stage_for_account(
            account=account,
            stage_type=PropStageType.STAGE_1,
            rules=firm.rules,
            balance=account_size
        )

        return account

    @classmethod
    def _create_stage_for_account(
        cls, account: PropAccount, stage_type: PropStageType, rules: PropFirmRules, balance: float
    ) -> PropStage:
        target_pct = (
            rules.target_stage_1_pct if stage_type == PropStageType.STAGE_1
            else (rules.target_stage_2_pct if stage_type == PropStageType.STAGE_2 else None)
        )
        profit_target = (balance * (target_pct / 100.0)) if target_pct is not None else None

        max_daily_loss = balance * (rules.max_daily_dd_pct / 100.0)
        max_total_loss = balance * (rules.max_total_dd_pct / 100.0)

        stage = PropStage(
            id=cls._stage_id_counter,
            account_id=account.id,
            stage_type=stage_type,
            initial_balance=balance,
            current_balance=balance,
            equity=balance,
            profit_target=profit_target,
            max_daily_loss_limit=max_daily_loss,
            max_total_loss_limit=max_total_loss,
            status=AccountStatus.ACTIVE,
        )
        cls.stages_db[stage.id] = stage
        cls._stage_id_counter += 1
        return stage

    @classmethod
    def update_stage_equity(cls, stage_id: int, current_equity: float, day_start_equity: float) -> Dict[str, Any]:
        """
        بروزرسانی وضعیت حساب و بررسی هشدارهای دراودان روزانه و کل
        """
        stage = cls.stages_db.get(stage_id)
        if not stage or stage.status != AccountStatus.ACTIVE:
            raise ValueError("Active stage not found.")

        stage.equity = current_equity
        net_pnl = current_equity - stage.initial_balance
        stage.current_balance = current_equity

        # بروزرسانی سود جاری حساب
        account = cls.accounts_db.get(stage.account_id)
        if account:
            account.current_profit = round(net_pnl, 2)

        # محاسبه دراودان روزانه و کل جاری
        daily_loss = max(0.0, day_start_equity - current_equity)
        total_loss = max(0.0, stage.initial_balance - current_equity)

        warnings = cls.check_drawdown_warnings(stage, daily_loss, total_loss)

        # بررسی فیل شدن خودکار
        if daily_loss >= stage.max_daily_loss_limit:
            cls.fail_stage(stage.id, reason=f"تخطی از حد دراودان روزانه (Loss: {daily_loss:.2f})")
        elif total_loss >= stage.max_total_loss_limit:
            cls.fail_stage(stage.id, reason=f"تخطی از حد دراودان کل (Loss: {total_loss:.2f})")

        return {
            "stage_id": stage.id,
            "equity": current_equity,
            "daily_loss": round(daily_loss, 2),
            "total_loss": round(total_loss, 2),
            "warnings": warnings,
            "status": stage.status
        }

    @classmethod
    def check_drawdown_warnings(cls, stage: PropStage, daily_loss: float, total_loss: float, threshold_pct: float = 80.0) -> List[str]:
        """
        هشدار خودکار در صورت نزدیک شدن به حد مجاز Daily DD یا Total DD (مثلاً رسیدن به ۸۰٪ حد مجاز)
        """
        warnings = []
        daily_threshold = stage.max_daily_loss_limit * (threshold_pct / 100.0)
        total_threshold = stage.max_total_loss_limit * (threshold_pct / 100.0)

        if daily_loss >= daily_threshold:
            pct_used = (daily_loss / stage.max_daily_loss_limit) * 100
            warnings.append(f"هشدار: {pct_used:.1f}% از حد دراودان روزانه استفاده شده است.")

        if total_loss >= total_threshold:
            pct_used = (total_loss / stage.max_total_loss_limit) * 100
            warnings.append(f"هشدار: {pct_used:.1f}% از حد دراودان کل استفاده شده است.")

        return warnings

    @classmethod
    def pass_stage(cls, stage_id: int) -> PropStage:
        """
        انتقال دستی به Stage 2 یا Funded پس از برآورده شدن شرایط
        """
        stage = cls.stages_db.get(stage_id)
        if not stage or stage.status != AccountStatus.ACTIVE:
            raise ValueError("Stage is not active or found.")

        account = cls.accounts_db.get(stage.account_id)
        firm = cls.firms_db.get(account.firm_id)

        stage.status = AccountStatus.PASSED
        stage.passed_at = datetime.utcnow()

        # انتقال به مرحله بعدی
        if stage.stage_type == PropStageType.STAGE_1:
            account.current_stage_type = PropStageType.STAGE_2
            cls._create_stage_for_account(account, PropStageType.STAGE_2, firm.rules, account.account_size)
        elif stage.stage_type == PropStageType.STAGE_2:
            account.current_stage_type = PropStageType.FUNDED
            account.status = AccountStatus.ACTIVE
            cls._create_stage_for_account(account, PropStageType.FUNDED, firm.rules, account.account_size)

        return stage

    @classmethod
    def fail_stage(cls, stage_id: int, reason: str) -> PropStage:
        """
        ثبت علت فیل شدن و بستن اکانت
        """
        stage = cls.stages_db.get(stage_id)
        if not stage:
            raise ValueError("Stage not found.")

        stage.status = AccountStatus.FAILED
        stage.failure_reason = reason

        account = cls.accounts_db.get(stage.account_id)
        if account:
            account.status = AccountStatus.CLOSED

        return stage

    @classmethod
    def process_withdrawal(cls, account_id: int, amount: float) -> PropWithdrawal:
        """
        محاسبه و ثبت برداشت سود فقط برای حساب‌های Funded
        """
        account = cls.accounts_db.get(account_id)
        if not account or account.current_stage_type != PropStageType.FUNDED:
            raise ValueError("برداشت فقط برای حساب‌های مرحله Real/Funded امکان‌پذیر است.")

        if account.current_profit < amount:
            raise ValueError(f"موجودی سود کافی نیست. سود جاری: {account.current_profit}")

        firm = cls.firms_db.get(account.firm_id)
        split_rate = firm.rules.profit_split_pct / 100.0 if firm else 0.8
        trader_share = amount * split_rate

        account.current_profit -= amount
        account.total_withdrawn += trader_share

        withdrawal = PropWithdrawal(
            id=cls._withdrawal_id_counter,
            account_id=account.id,
            amount=amount,
            trader_share_amount=trader_share,
        )
        cls.withdrawals_db.append(withdrawal)
        cls._withdrawal_id_counter += 1

        return withdrawal

    @classmethod
    def get_desk_analytics(cls) -> Dict[str, Any]:
        """
        خلاصه وضعیت تمام حساب‌های پراپ برای مدیریت
        """
        total_accounts = len(cls.accounts_db)
        active_accounts = sum(1 for a in cls.accounts_db.values() if a.status == AccountStatus.ACTIVE)
        closed_accounts = sum(1 for a in cls.accounts_db.values() if a.status == AccountStatus.CLOSED)

        funded_capital = sum(
            a.account_size for a in cls.accounts_db.values()
            if a.current_stage_type == PropStageType.FUNDED and a.status == AccountStatus.ACTIVE
        )

        total_payouts = sum(w.trader_share_amount for w in cls.withdrawals_db)

        stage_distribution = {
            PropStageType.STAGE_1.value: sum(1 for a in cls.accounts_db.values() if a.current_stage_type == PropStageType.STAGE_1 and a.status == AccountStatus.ACTIVE),
            PropStageType.STAGE_2.value: sum(1 for a in cls.accounts_db.values() if a.current_stage_type == PropStageType.STAGE_2 and a.status == AccountStatus.ACTIVE),
            PropStageType.FUNDED.value: sum(1 for a in cls.accounts_db.values() if a.current_stage_type == PropStageType.FUNDED and a.status == AccountStatus.ACTIVE),
        }

        return {
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "closed_accounts": closed_accounts,
            "total_funded_capital": funded_capital,
            "total_payouts_claimed": round(total_payouts, 2),
            "stage_distribution": stage_distribution,
            "pass_rate_pct": round(((active_accounts - stage_distribution[PropStageType.STAGE_1.value]) / total_accounts * 100), 2) if total_accounts > 0 else 0.0
        }