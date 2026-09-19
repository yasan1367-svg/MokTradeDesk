import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

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
  personalAccountId?: number,
) => {
  const formData = new FormData();
  formData.append('file', file);
  if (versionId) formData.append('version_id', versionId.toString());
  if (propStageId) formData.append('prop_stage_id', propStageId.toString());
  if (personalAccountId) formData.append('personal_account_id', personalAccountId.toString());
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
  personalAccountId?: number,
) => {
  const formData = new FormData();
  formData.append('file', file);
  if (versionId) formData.append('version_id', versionId.toString());
  if (propStageId) formData.append('prop_stage_id', propStageId.toString());
  if (personalAccountId) formData.append('personal_account_id', personalAccountId.toString());
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

export const withdrawFromStage = (
  stageId: number,
  amount: number,
  note?: string,
  targetPersonalAccountId?: number
) =>
  api.post(`/api/prop/stages/${stageId}/withdraw`, {
    amount,
    note,
    target_personal_account_id: targetPersonalAccountId,
  });
export const getStageWithdrawals = (stageId: number) =>
  api.get(`/api/prop/stages/${stageId}/withdrawals`);

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

export const updateVersion = (
  versionId: number,
  data: { version_name?: string; rules_note?: string; status?: string }
) => api.patch(`/api/strategies/versions/${versionId}`, data);

export const deleteVersion = (versionId: number) =>
  api.delete(`/api/strategies/versions/${versionId}`);


// ─────────────────────────────────────────────
// Trades Management
// ─────────────────────────────────────────────
export const getTrades = (params?: {
  version_id?: number;
  prop_stage_id?: number;
  symbol?: string;
  test_type?: string;
  source?: string;
  search?: string;
  limit?: number;
  offset?: number;
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
  personal_account_id?: number;
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
// Personal Accounts & Accounting
// ─────────────────────────────────────────────
export const getPersonalAccounts = () => api.get('/api/personal/accounts');

export const createPersonalAccount = (data: {
  name: string;
  broker_name: string;
  account_number?: string;
  currency?: string;
  initial_balance?: number;
}) => api.post('/api/personal/accounts', data);

export const getPersonalAccountDetail = (accountId: number) =>
  api.get(`/api/personal/accounts/${accountId}`);

export const updatePersonalAccount = (accountId: number, data: any) =>
  api.patch(`/api/personal/accounts/${accountId}`, data);

export const deletePersonalAccount = (accountId: number) =>
  api.delete(`/api/personal/accounts/${accountId}`);

// ─────────────────────────────────────────────
// Ledger
// ─────────────────────────────────────────────
export const getLedger = (params?: {
  personal_account_id?: number;
  transaction_type?: string;
  from_date?: string;
  to_date?: string;
  limit?: number;
}) => api.get('/api/personal/ledger', { params });

export const createLedgerTransaction = (data: {
  transaction_type: string;
  amount: number;
  currency?: string;
  description?: string;
  personal_account_id?: number;
  prop_account_id?: number;
  transaction_date?: string;
}) => api.post('/api/personal/ledger', data);

export const deleteLedgerTransaction = (transactionId: number) =>
  api.delete(`/api/personal/ledger/${transactionId}`);

export const getCashflow = (params?: { from_date?: string; to_date?: string }) =>
  api.get('/api/personal/cashflow', { params });

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

export const getPropAccountsForLedger = () =>
  api.get('/api/personal/prop-accounts-list');
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

