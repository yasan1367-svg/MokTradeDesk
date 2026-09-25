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
export const createVersion = (strategyId: number, data: { version_name: string; rules_note?: string }) =>
  api.post(`/api/strategies/${strategyId}/versions`, data);

// ─────────────────────────────────────────────
// Analytics
// ─────────────────────────────────────────────
export const analyzeVersion = (versionId: number) =>
  api.post(`/api/analytics/analyze/${versionId}`);
export const getAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);
export const compareVersions = (versionIds: number[], minTrades: number = 0) =>
  api.post('/api/analytics/compare', { version_ids: versionIds, min_trades: minTrades });
export const getIntervals = (symbol?: string) =>
  api.get('/api/analytics/intervals/', { params: symbol ? { symbol } : {} });
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
export const getDashboardData = () => api.get('/api/analytics/dashboard');

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
// Analytics Detail
// ─────────────────────────────────────────────
export const getVersionTrades = (versionId: number) =>
  api.get(`/api/strategies/versions/${versionId}/trades`);

export const getVersionAnalysis = (versionId: number) =>
  api.get(`/api/analytics/${versionId}`);

export const getVersionAnalysisHistory = (versionId: number) =>
  api.get(`/api/analytics/${versionId}/history`);

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
  create_finance_account?: boolean;  // 🆕 فاز ۵.۱ — ساخت خودکار حساب مالی
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

// 🆕 فاز ۵.۱ — حساب مالی متناظر با یک اکانت پراپ
export const getPropAccountFinanceAccount = (propAccountId: number) =>
  api.get(`/api/prop/accounts/${propAccountId}/finance-account`);

// 🆕 فاز ۵.۱ — ساخت (یا اتصال) حساب مالی برای اکانت پراپ
export const createPropFinanceAccount = (propAccountId: number) =>
  api.post(`/api/prop/accounts/${propAccountId}/finance-account`);

// 🆕 فاز ۵.۱ — حساب‌های مالی مجاز به‌عنوان مقصد برداشت
// (فیلتر type !== 'prop' در سمت کلاینت انجام می‌شود)
export const getFinanceAccountsForDestination = () =>
  api.get('/api/finance/accounts');

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
  data: { version_name?: string; rules_note?: string; status?: string }
) => api.patch(`/api/strategies/versions/${versionId}`, data);

export const deleteVersion = (versionId: number) =>
  api.delete(`/api/strategies/versions/${versionId}`);

export const forkVersion = (versionId: number) =>
  api.post(`/api/strategies/versions/${versionId}/fork`);


// ─────────────────────────────────────────────
// Trades Management
// ─────────────────────────────────────────────
export const getTrades = (params?: {
  version_id?: number;
  prop_stage_id?: number;
  symbol?: string;
  test_type?: string;
  source?: string;
  direction?: string;
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

export const deleteTrade = (tradeId: number) =>
  api.delete(`/api/trades/${tradeId}`);

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
  finance_account_id?: number;
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
  broker_name?: string;
  prop_firm_name?: string;
  prop_firm_id?: number | null;
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
