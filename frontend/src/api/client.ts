import axios from 'axios';

const API_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) 
  || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ─────────────────────────────────────────────
// Strategies
// ─────────────────────────────────────────────
export const getStrategies = () => api.get('/api/strategies/');
export const createStrategy = (data: { name: string; description?: string }) =>
  api.post('/api/strategies/', data);
export const createVersion = (strategyId: number, data: { version_name: string; rules_note?: string; test_type?: string; status?: string }) =>
  api.post(`/api/strategies/${strategyId}/versions`, data);

// ─────────────────────────────────────────────
// Analytics
// ─────────────────────────────────────────────
export const analyzeVersion = (versionId: number) =>
  api.post(`/api/analytics/analyze/${versionId}`);
export const getAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);
export const getIntervals = (symbol?: string) =>
  api.get('/api/analytics/intervals/', { params: symbol ? { symbol } : {} });
// فاز ۱۵.۸: تابع تکراری compareVersions حذف شد — این نسخهٔ واحد استفاده می‌شود
export const compareVersionsWithDetails = (versionIds: number[], minTrades: number = 0) =>
  api.post('/api/analytics/compare', { version_ids: versionIds, min_trades: minTrades });
export const getPropAnalytics = () => api.get('/api/prop/analytics');

export const getFirmDefaultRules = (firmId: number) =>
  api.get(`/api/prop/firms/${firmId}/default-rules`);

// ─────────────────────────────────────────────
// Prop Alerts
// ─────────────────────────────────────────────
export const getPropAlerts = (params?: { stage_id?: number; unread_only?: boolean }) =>
  api.get('/api/prop/alerts', { params });

export const markAlertRead = (alertId: number) =>
  api.patch(`/api/prop/alerts/${alertId}/read`);

export const generatePropAlerts = () =>
  api.post('/api/prop/alerts/generate');

// ─────────────────────────────────────────────
// Calendar
// ─────────────────────────────────────────────
export const getCalendarData = (params?: {
  year?: number;
  month?: number;
  from_date?: string;
  to_date?: string;
}) => api.get('/api/analytics/calendar', { params });

// ─────────────────────────────────────────────
// Dashboard
// ─────────────────────────────────────────────
export const getDashboardData = (params?: { date_from?: string; date_to?: string }) =>
  api.get('/api/analytics/dashboard', { params });

export const getYesterdayData = () => api.get('/api/analytics/yesterday');

export const getRiskAdvanced = (params?: { date_from?: string; date_to?: string }) =>
  api.get('/api/analytics/risk-advanced', { params });

// ─────────────────────────────────────────────
// Risk Management
// ─────────────────────────────────────────────
export const getRiskMetrics = () => api.get('/api/analytics/risk-metrics');

// ─────────────────────────────────────────────
// Export
// ─────────────────────────────────────────────
export const exportTradesCsv = (params?: Record<string, any>) =>
  api.get('/api/export/trades/csv', { params, responseType: 'blob' });
export const exportTradesPdf = (params?: Record<string, any>) =>
  api.get('/api/export/trades/pdf', { params, responseType: 'blob' });
export const exportAnalysisPdf = (versionId: number) =>
  api.get('/api/export/analysis/pdf', { params: { version_id: versionId }, responseType: 'blob' });
export const exportDashboardPdf = () =>
  api.get('/api/export/dashboard/pdf', { responseType: 'blob' });
// ─────────────────────────────────────────────
// Import
// ─────────────────────────────────────────────
export const getAllVersions = () => api.get('/api/strategies/versions/all');

export const importSoft4X = (
  file: File,
  versionId?: number,
  symbol?: string,
  testType?: string,
  propStageId?: number,
) => {
  const formData = new FormData();
  formData.append('file', file);
  if (versionId) formData.append('version_id', versionId.toString());
  if (propStageId) formData.append('prop_stage_id', propStageId.toString());
  if (symbol) formData.append('symbol', symbol);
  if (testType) formData.append('test_type', testType);

  return api.post('/api/imports/soft4x', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const importMT4 = (
  file: File,
  versionId?: number,
  testType?: string,
  propStageId?: number,
) => {
  const formData = new FormData();
  formData.append('file', file);
  if (versionId) formData.append('version_id', versionId.toString());
  if (propStageId) formData.append('prop_stage_id', propStageId.toString());
  if (testType) formData.append('test_type', testType);

  return api.post('/api/imports/mt4', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// ─────────────────────────────────────────────
// Import Engine (فاز ۳۰/۳۱) — Preview / Commit / Batches / Profiles
// ─────────────────────────────────────────────
export type ImportSourceFormat = 'soft4x_xlsx' | 'mt4_html';

export interface ImportOptions {
  versionId?: number;
  propStageId?: number;
  personalTradingAccountId?: number;
  symbol?: string;
  testType?: string;
  profileId?: number;
  columnMapping?: Record<string, any>;
  symbolMapping?: Record<string, string>;
}

const buildImportFormData = (
  file: File,
  sourceFormat: ImportSourceFormat,
  options: ImportOptions = {},
) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('source_format', sourceFormat);
  if (options.versionId) formData.append('version_id', options.versionId.toString());
  if (options.propStageId) formData.append('prop_stage_id', options.propStageId.toString());
  if (options.personalTradingAccountId)
    formData.append('personal_trading_account_id', options.personalTradingAccountId.toString());
  if (options.profileId) formData.append('profile_id', options.profileId.toString());
  if (options.symbol) formData.append('symbol', options.symbol);
  if (options.testType) formData.append('test_type', options.testType);
  if (options.columnMapping)
    formData.append('column_mapping', JSON.stringify(options.columnMapping));
  if (options.symbolMapping)
    formData.append('symbol_mapping', JSON.stringify(options.symbolMapping));
  return formData;
};

/** مرحله‌ی Preview — هیچ معامله‌ای ساخته نمی‌شود؛ فقط staging + تشخیص تکرار */
export const previewImport = (
  file: File,
  sourceFormat: ImportSourceFormat,
  options: ImportOptions = {},
) =>
  api.post('/api/imports/preview', buildImportFormData(file, sourceFormat, options), {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

/** مرحله‌ی تأیید کاربر — Commit اتمیک روی همان batch */
export const commitImport = (batchId: number, allowPossibleDuplicates = false) =>
  api.post(`/api/imports/commit/${batchId}`, {
    allow_possible_duplicates: allowPossibleDuplicates,
  });

export const cancelImportBatch = (batchId: number) =>
  api.post(`/api/imports/batches/${batchId}/cancel`);

export const getImportBatches = (params?: { limit?: number; status?: string }) =>
  api.get('/api/imports/batches', { params });

export const getImportBatch = (
  batchId: number,
  params?: { include_rows?: boolean; rows_limit?: number },
) => api.get(`/api/imports/batches/${batchId}`, { params });

export const getImportProfiles = (includeInactive = true) =>
  api.get('/api/imports/profiles', { params: { include_inactive: includeInactive } });

export const createImportProfile = (payload: Record<string, any>) =>
  api.post('/api/imports/profiles', payload);

export const updateImportProfile = (profileId: number, payload: Record<string, any>) =>
  api.patch(`/api/imports/profiles/${profileId}`, payload);

export const deleteImportProfile = (profileId: number) =>
  api.delete(`/api/imports/profiles/${profileId}`);


// ─────────────────────────────────────────────
// Analytics Detail
// ─────────────────────────────────────────────
export const getVersionTrades = (versionId: number) =>
  api.get(`/api/strategies/versions/${versionId}/trades`);

export const getVersionAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);

export const getVersionAnalysisHistory = (versionId: number) =>
  api.get(`/api/analytics/${versionId}/history`);

// ─────────────────────────────────────────────
// فاز ۲۰.۳ — تحلیل ۶گانه (نوع + scope)
// ─────────────────────────────────────────────
export const analyzeVersionScoped = (versionId: number, testType?: string) =>
  api.post(`/api/analytics/analyze/version/${versionId}`, null,
    { params: testType ? { test_type: testType } : {} });
export const analyzePropStage = (propStageId: number) =>
  api.post(`/api/analytics/analyze/prop/${propStageId}`);
export const getAnalysisVersion = (versionId: number, testType?: string) =>
  api.get(`/api/analytics/analysis/version/${versionId}`,
    { params: testType ? { test_type: testType } : {} });
export const getAnalysisProp = (propStageId: number) =>
  api.get(`/api/analytics/analysis/prop/${propStageId}`);
// فاز ۳۸.۴ (Clean Break): `analyzeBroker`/`getAnalysisBroker` حذف شدند
// (مسیرهای `/analyze|analysis/broker/{id}` در بک‌اند وجود ندارند؛ معادل آن‌ها
//  `/analyze|analysis/personal-account/{personal_trading_account_id}` است).

// ─────────────────────────────────────────────
// Prop Desk
// ─────────────────────────────────────────────
export const getPropFirms = () => api.get('/api/prop/firms');
export const createPropFirm = (data: { name: string; default_profit_share?: number; website?: string }) =>
  api.post('/api/prop/firms', data);

export const getPropAccounts = () => api.get('/api/prop/accounts');
export const createPropAccount = (data: {
  prop_firm_id: number;
  account_label: string;
  account_number?: string;
  currency?: string;
  initial_balance?: number;
  profit_target?: number;
  max_daily_dd?: number;
  max_total_dd?: number;
  min_trading_days?: number;
}) => api.post('/api/prop/accounts', data);

export const getPropAccountDetail = (accountId: number) =>
  api.get(`/api/prop/accounts/${accountId}`);

export const passStage = (stageId: number, finalBalance?: number) =>
  api.post(`/api/prop/stages/${stageId}/pass`, { final_balance: finalBalance });

export const failStage = (stageId: number, failureReason: string, failureDetails?: string) =>
  api.post(`/api/prop/stages/${stageId}/fail`, {
    failure_reason: failureReason,
    failure_details: failureDetails,
  });

// 🆕 فاز ۵.۱ — برداشت از پراپ: مقصد = حساب مالی (جایگزین اکانت شخصی)
export const withdrawFromStage = (
  stageId: number,
  data: {
    amount: number;
    destination_account_id: number;
    withdrawal_date?: string;
    note?: string;
  }
) => api.post(`/api/prop/stages/${stageId}/withdraw`, data);

export const getStageWithdrawals = (stageId: number) =>
  api.get(`/api/prop/stages/${stageId}/withdrawals`);

// فاز ۳۸.۵: `getPropAccountFinanceAccount` / `createPropFinanceAccount` حذف شدند
// (endpointهای `/api/prop/accounts/{id}/finance-account` در فاز ۲۸ حذف شده‌اند).

// 🆕 فاز ۵.۱ — حساب‌های مالی مجاز به‌عنوان مقصد برداشت
// (فیلتر type !== 'prop' در سمت کلاینت انجام می‌شود)
export const getFinanceAccountsForDestination = () =>
  api.get('/api/finance/accounts');

// ─────────────────────────────────────────────
// Trading (فاز ۲۸ / ۳۸.۵) — بروکرها + حساب‌های معاملاتی شخصی
// دامنهٔ TRADING جدا از FINANCE است: منبع درست برای کلاسیفیکیشن REAL_PERSONAL.
// ─────────────────────────────────────────────
export const getBrokers = () => api.get('/api/trading/brokers');

/** حساب‌های معاملاتی شخصی (هر کدام روی یک بروکر) — برای انتخاب دامنهٔ معاملهٔ REAL_PERSONAL */
export const getPersonalTradingAccounts = (params?: { broker_id?: number }) =>
  api.get('/api/trading/accounts', { params });

export const getStageTrades = (stageId: number) =>
  api.get(`/api/prop/stages/${stageId}/trades`);

export const getAllPropStages = () => api.get('/api/prop/stages/all');

export const checkPassReady = (stageId: number) =>
  api.get(`/api/prop/stages/${stageId}/check-pass`);

export const passStageWithRules = (
  stageId: number,
  finalBalance?: number,
  nextStageRules?: {
    profit_target?: number;
    max_daily_dd?: number;
    max_total_dd?: number;
    min_trading_days?: number;
    initial_balance?: number;
    profit_share_percentage?: number;
  }
) =>
  api.post(`/api/prop/stages/${stageId}/pass`, {
    final_balance: finalBalance,
    next_stage_rules: nextStageRules,
  });

export const updateStageRules = (
  stageId: number,
  data: {
    profit_target?: number;
    max_daily_dd?: number;
    max_total_dd?: number;
    min_trading_days?: number;
    initial_balance?: number;
    profit_share_percentage?: number;
  }
) => api.patch(`/api/prop/stages/${stageId}/rules`, data);

export const getActivePropStages = () => api.get('/api/prop/stages/all');

// ─────────────────────────────────────────────
// Strategy Management
// ─────────────────────────────────────────────
export const getStrategyDetail = (strategyId: number) =>
  api.get(`/api/strategies/${strategyId}`);

export const updateStrategy = (strategyId: number, data: { name?: string; description?: string }) =>
  api.patch(`/api/strategies/${strategyId}`, data);

export const deleteStrategy = (strategyId: number) =>
  api.delete(`/api/strategies/${strategyId}`);

export const getStrategyVersions = (strategyId: number) =>
  api.get(`/api/strategies/${strategyId}/versions`);
export const getStrategyStats = (strategyId: number) =>
  api.get(`/api/strategies/${strategyId}/stats`);

export const updateVersion = (
  versionId: number,
  data: { version_name?: string; rules_note?: string; status?: string; test_type?: string }
) => api.patch(`/api/strategies/versions/${versionId}`, data);

export const deleteVersion = (versionId: number) =>
  api.delete(`/api/strategies/versions/${versionId}`);

export const forkVersion = (
  versionId: number,
  data?: { version_name?: string; rules_note?: string; test_type?: string; status?: string }
) =>
  api.post(`/api/strategies/versions/${versionId}/fork`, data ?? {});


// ─────────────────────────────────────────────
// Trades Management
// ─────────────────────────────────────────────
export const getTrades = (params?: {
  version_id?: number;
  prop_stage_id?: number;
  personal_trading_account_id?: number;  // فاز ۳۸.۴: جایگزین منسوخ `finance_account_id`
  symbol?: string;
  test_type?: string;
  source?: string;
  direction?: string;
  status?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  pnl_min?: number;
  pnl_max?: number;
  page?: number;
  page_size?: number;
  limit?: number;
  offset?: number;
  sort_by?: string;
  sort_order?: string;
}) => api.get('/api/trades/', { params });

export const getTrade = (tradeId: number) =>
  api.get(`/api/trades/${tradeId}`);

export const updateTrade = (tradeId: number, data: { note?: string }) =>
  api.patch(`/api/trades/${tradeId}`, data);

// فاز ۲۵: حذف نرم (Soft Delete) پیش‌فرض است. برای حذف کامل (ادمین) hard=true بدهید.
export const deleteTrade = (tradeId: number, hard = false) =>
  api.delete(`/api/trades/${tradeId}`, { params: hard ? { hard: true } : {} });

// فاز ۲۵: حذف گروهی معاملات (پیش‌فرض Soft Delete)
export const batchDeleteTrades = (tradeIds: number[], hard = false) =>
  api.post('/api/trades/batch-delete', { trade_ids: tradeIds, hard });

export const createManualTrade = (data: {
  symbol: string;
  direction: string;
  open_time: string;
  close_time?: string;
  open_price: number;
  close_price?: number;
  size: number;
  sl?: number;
  tp?: number;
  pnl?: number;
  commission?: number;
  swap?: number;
  version_id?: number;
  // فاز ۳۸.۵: جایگزین منسوخ `finance_account_id` (که در بک‌اند وجود نداشت).
  // قرارداد Trade (فاز ۲۷): REAL_PERSONAL ⇒ personal_trading_account_id، REAL_PROP ⇒ prop_stage_id
  personal_trading_account_id?: number;
  prop_stage_id?: number;
  test_type?: string;
  note?: string;
}) => api.post('/api/trades/manual', data);

export const uploadTradeScreenshot = (tradeId: number, file: File, description?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  if (description) formData.append('description', description);
  return api.post(`/api/trades/${tradeId}/screenshots`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getTradeScreenshots = (tradeId: number) =>
  api.get(`/api/trades/${tradeId}/screenshots`);

export const deleteScreenshot = (screenshotId: number) =>
  api.delete(`/api/trades/screenshots/${screenshotId}`);

// ─────────────────────────────────────────────
// Journal
// ─────────────────────────────────────────────
export const createJournalReview = (data: {
  trade_id: number;
  setup_quality?: number;
  execution_quality?: number;
  rule_violations?: string;
  notes?: string;
  lessons?: string;
  rating?: number;
}) => api.post('/api/personal/journal/review', data);

export const getJournalReviews = () => api.get('/api/personal/journal/reviews');

export const uploadReviewScreenshot = (reviewId: number, file: File, description?: string) => {
  const formData = new FormData();
  formData.append('file', file);
  if (description) formData.append('description', description);
  return api.post(`/api/personal/journal/reviews/${reviewId}/screenshots`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export const getReviewScreenshots = (reviewId: number) =>
  api.get(`/api/personal/journal/reviews/${reviewId}/screenshots`);

export const deleteReviewScreenshot = (screenshotId: number) =>
  api.delete(`/api/personal/journal/reviews/screenshots/${screenshotId}`);

export const deleteJournalReview = (reviewId: number) =>
  api.delete(`/api/personal/journal/reviews/${reviewId}`);

// ─────────────────────────────────────────────
// Symbol Mappings
// ─────────────────────────────────────────────
export const getSymbolMappings = () => api.get('/api/symbol-mappings/');

export const createSymbolMapping = (data: {
  original_symbol: string;
  canonical_symbol: string;
  description?: string;
}) => api.post('/api/symbol-mappings/', data);

export const updateSymbolMapping = (
  id: number,
  data: {
    original_symbol?: string;
    canonical_symbol?: string;
    description?: string;
  }
) => api.patch(`/api/symbol-mappings/${id}`, data);

export const deleteSymbolMapping = (id: number) =>
  api.delete(`/api/symbol-mappings/${id}`);

export const seedSymbolMappings = () =>
  api.post('/api/symbol-mappings/seed-defaults');





// ─────────────────────────────────────────────
// Settings
// ─────────────────────────────────────────────
export const getSettings = () => api.get('/api/settings/');

export const updateSettings = (data: {
  theme?: string;
  font_size?: number;
  timezone?: string;
  currency?: string;
  calendar?: string;
  default_risk_percent?: number;
  default_profit_share?: number;
}) => api.patch('/api/settings/', data);

// ─────────────────────────────────────────────
// Finance
// ─────────────────────────────────────────────
export const getFinanceAccounts = (params?: { type?: string; currency?: string }) =>
  api.get('/api/finance/accounts', { params });

export const createFinanceAccount = (data: {
  name: string;
  type: string;
  currency?: string;
  balance?: number;
  card_number?: string;
}) => api.post('/api/finance/accounts', data);

export const updateFinanceAccount = (id: number, data: Record<string, any>) =>
  api.patch(`/api/finance/accounts/${id}`, data);

export const deleteFinanceAccount = (id: number) =>
  api.delete(`/api/finance/accounts/${id}`);

export const getFinanceCategories = (params?: { type?: string }) =>
  api.get('/api/finance/categories', { params });

export const createFinanceCategory = (data: {
  name: string;
  type: string;
  color?: string;
  icon?: string;
}) => api.post('/api/finance/categories', data);

export const updateFinanceCategory = (id: number, data: Record<string, any>) =>
  api.patch(`/api/finance/categories/${id}`, data);

export const deleteFinanceCategory = (id: number) =>
  api.delete(`/api/finance/categories/${id}`);

export const getFinanceTransactions = (params?: {
  date_from?: string;
  date_to?: string;
  account_id?: number;
  type?: string;
  category_id?: number;
}) => api.get('/api/finance/transactions', { params });

export const createFinanceTransaction = (data: {
  account_id: number;
  amount: number;
  type: string;
  category_id?: number | null;
  currency?: string;
  date?: string;
  description?: string;
  from_account_id?: number | null;
  to_account_id?: number | null;
  related_trade_id?: number | null;
  related_prop_account_id?: number | null;
}) => api.post('/api/finance/transactions', data);

export const updateFinanceTransaction = (id: number, data: Record<string, any>) =>
  api.patch(`/api/finance/transactions/${id}`, data);

export const deleteFinanceTransaction = (id: number) =>
  api.delete(`/api/finance/transactions/${id}`);

export const seedFinanceCategories = () => api.post('/api/finance/seed');

// ─────────────────────────────────────────────
// Finance Reports
// ─────────────────────────────────────────────
export const getFinanceSummary = () =>
  api.get('/api/finance/summary');

export const getFinanceAccountStats = (accountId: number) =>
  api.get(`/api/finance/accounts/${accountId}/stats`);

export const getFinanceWithdrawalStats = () =>
  api.get('/api/finance/withdrawals/stats');

export const getFinanceCashflow = (params?: { year?: number }) =>
  api.get('/api/finance/charts/cashflow', { params });

export const getFinanceDistribution = (params?: {
  date_from?: string;
  date_to?: string;
}) => api.get('/api/finance/charts/distribution', { params });

// ─────────────────────────────────────────────
// Advanced Finance Reports (فاز ۱۱)
// ─────────────────────────────────────────────
export const getFinanceMonthlyReport = (params?: { year?: number; account_id?: number }) =>
  api.get('/api/finance/reports/monthly', { params });

export const getFinanceCategoryBreakdown = (params?: {
  year?: number;
  month?: number;
  type?: string;
  account_id?: number;
}) => api.get('/api/finance/reports/category-breakdown', { params });

export const getFinanceAccountComparison = (params?: {
  year?: number;
  month?: number;
  currency?: string;
}) => api.get('/api/finance/reports/account-comparison', { params });

export const getFinanceProfitLoss = (params?: { year?: number; account_id?: number }) =>
  api.get('/api/finance/reports/profit-loss', { params });

// ─────────────────────────────────────────────
// Finance Reports — فاز ۲۲
// ─────────────────────────────────────────────
export type AssetBucket = { amount: number; currency: string };

export const getSpendableAssets = () =>
  api.get<Record<string, AssetBucket> & { total: { usd: number; irr: number } }>(
    '/api/finance/spendable-assets',
  );

export const getRealPnl = () =>
  api.get<{
    prop_stage_3: { pnl: number; trades: number };
    broker: { pnl: number; trades: number };
    total: { pnl: number; trades: number };
  }>('/api/finance/real-pnl');

export const getNetProfit = () =>
  api.get<{ real_pnl: number; expenses: number; net_profit: number }>(
    '/api/finance/net-profit',
  );

export type MoneyFlow = {
  from: string | null; to: string | null; amount: number;
  currency: string | null; type: string | null; date?: string | null;
};
export const getMoneyFlow = () =>
  api.get<{ flows: MoneyFlow[] }>('/api/finance/money-flow');

export type ExpensesBreakdown = {
  prop_purchase: number; prop_subscription: number; exchange_fee: number;
  withdrawal_fee: number; other: number; total: number;
};
export const getFinanceExpenses = () =>
  api.get<ExpensesBreakdown>('/api/finance/expenses');

export const getMoneyCycle = () =>
  api.get<{
    total_deposits: number; total_withdrawals: number; total_exchanges: number;
    total_transfers: number; current_balance: number;
  }>('/api/finance/money-cycle');

export type CalendarDay = {
  date: string; pnl: number; trades: number; deposits: number; withdrawals: number;
};
export const getFinancialCalendar = () =>
  api.get<{ days: CalendarDay[] }>('/api/finance/financial-calendar');

export const getAssetTrend = (params?: { date_from?: string; date_to?: string }) =>
  api.get<{ trend: { date: string; total_usd: number; total_irr: number }[] }>(
    '/api/finance/asset-trend', { params },
  );

export const getExchangeRates = () =>
  api.get<{ rates: { date: string; from: string; to: string; rate: number }[] }>(
    '/api/finance/exchange-rates',
  );

// ─────────────────────────────────────────────
// Payout History (فاز ۱۶)
// ─────────────────────────────────────────────
export type PayoutFilters = {
  firm_id?: number;
  currency?: string;
  date_from?: string;
  date_to?: string;
};

export const getPropPayouts = (params?: PayoutFilters) =>
  api.get('/api/prop/payouts', { params });

export const getPropPayoutsStats = (params?: PayoutFilters) =>
  api.get('/api/prop/payouts/stats', { params });

export const createPropPayout = (data: {
  prop_stage_id: number;
  amount: number;
  note?: string;
  destination_account_id: number;
  withdrawal_date?: string;
  // فاز ۳۳
  currency?: string;
  reference?: string;
  status?: string;
}) => api.post('/api/prop/payouts', data);

export const updatePropPayout = (id: number, data: Record<string, any>) =>
  api.put(`/api/prop/payouts/${id}`, data);

// فاز ۳۳ — چرخهٔ عمر برداشت (REQUESTED→APPROVED→PROCESSING→RECEIVED / CANCELLED)
export const updatePropPayoutStatus = (
  id: number,
  status: string,
  reference?: string,
) => api.post(`/api/prop/payouts/${id}/status`, { status, reference });

// فاز ۳۳ — ثبت یک پرش انتقال بعد از دریافت (درآمد نیست)
export const createPropPayoutTransfer = (
  id: number,
  data: {
    to_account_id: number;
    amount: number;
    from_account_id?: number;
    currency?: string;
    note?: string;
    date?: string;
  },
) => api.post(`/api/prop/payouts/${id}/transfer`, data);

export const deletePropPayout = (id: number) =>
  api.delete(`/api/prop/payouts/${id}`);

export const getBrokerPayouts = (params?: {
  account_id?: number;
  currency?: string;
  date_from?: string;
  date_to?: string;
}) => api.get('/api/broker/payouts', { params });

export const getBrokerPayoutsStats = (params?: {
  account_id?: number;
  currency?: string;
  date_from?: string;
  date_to?: string;
}) => api.get('/api/broker/payouts/stats', { params });

// ─────────────────────────────────────────────
// Backup (فاز ۱۷)
// ─────────────────────────────────────────────
export type BackupItem = {
  filename: string;
  size: number;
  created_at: string;
};

export const createBackup = () => api.post('/api/backup/create');

export const listBackups = () => api.get('/api/backup/list');

export const downloadBackup = (filename: string) =>
  api.get(`/api/backup/download/${encodeURIComponent(filename)}`, { responseType: 'blob' });

export const restoreBackup = (filename: string) =>
  api.post(`/api/backup/restore/${encodeURIComponent(filename)}`);

export const deleteBackup = (filename: string) =>
  api.delete(`/api/backup/${encodeURIComponent(filename)}`);

export const getBackupSettings = () => api.get('/api/backup/settings');

export const updateBackupSettings = (data: {
  auto_enabled?: boolean;
  interval_hours?: number;
  keep?: number;
}) => api.put('/api/backup/settings', data);

