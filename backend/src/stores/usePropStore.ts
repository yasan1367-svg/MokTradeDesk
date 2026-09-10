import { create } from 'zustand';

export type PropStageType = 'Stage 1' | 'Stage 2' | 'Funded';
export type AccountStatus = 'Active' | 'Passed' | 'Failed' | 'Closed';

export interface PropStage {
  id: number;
  account_id: number;
  stage_type: PropStageType;
  initial_balance: number;
  current_balance: number;
  equity: number;
  profit_target?: number;
  max_daily_loss_limit: number;
  max_total_loss_limit: number;
  status: AccountStatus;
  failure_reason?: string;
}

export interface PropAccount {
  id: number;
  firm_id: number;
  account_number: string;
  account_size: number;
  current_stage_type: PropStageType;
  status: AccountStatus;
  current_profit: number;
  total_withdrawn: number;
}

export interface PropAnalytics {
  total_accounts: number;
  active_accounts: number;
  closed_accounts: number;
  total_funded_capital: number;
  total_payouts_claimed: number;
  stage_distribution: Record<string, number>;
  pass_rate_pct: number;
}

interface PropState {
  accounts: PropAccount[];
  analytics: PropAnalytics | null;
  isLoading: boolean;
  error: string | null;
  fetchAccounts: () => Promise<void>;
  fetchAnalytics: () => Promise<void>;
  passStage: (stageId: number) => Promise<void>;
  failStage: (stageId: number, reason: string) => Promise<void>;
  withdraw: (accountId: number, amount: number) => Promise<void>;
}

export const usePropStore = create<PropState>((set, get) => ({
  accounts: [],
  analytics: null,
  isLoading: false,
  error: null,

  fetchAccounts: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch('/api/prop/accounts');
      const data = await res.json();
      set({ accounts: data, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchAnalytics: async () => {
    try {
      const res = await fetch('/api/prop/analytics');
      const data = await res.json();
      set({ analytics: data });
    } catch (err: any) {
      console.error(err);
    }
  },

  passStage: async (stageId: number) => {
    await fetch(`/api/prop/stages/${stageId}/pass`, { method: 'POST' });
    await get().fetchAccounts();
    await get().fetchAnalytics();
  },

  failStage: async (stageId: number, reason: string) => {
    await fetch(`/api/prop/stages/${stageId}/fail`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason }),
    });
    await get().fetchAccounts();
    await get().fetchAnalytics();
  },

  withdraw: async (accountId: number, amount: number) => {
    await fetch(`/api/prop/stages/${accountId}/withdraw`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ amount }),
    });
    await get().fetchAccounts();
    await get().fetchAnalytics();
  },
}));