import { create } from 'zustand';

export interface LedgerTransaction {
  id: number;
  account_id: number;
  category: string;
  type: 'Income' | 'Expense';
  amount: number;
  description?: string;
  reference_id?: string;
  timestamp: string;
}

export interface JournalEntry {
  id: number;
  trade_id: string;
  execution_quality: string;
  emotional_state: string;
  notes?: string;
  lessons_learned?: string;
  screenshot_url?: string;
}

export interface CashFlowReport {
  summary: {
    total_income: number;
    total_expense: number;
    net_cash_flow: number;
  };
  category_breakdown: Record<string, { income: number; expense: number; net: number }>;
}

interface LedgerState {
  transactions: LedgerTransaction[];
  cashFlow: CashFlowReport | null;
  isLoading: boolean;
  error: string | null;
  fetchTransactions: () => Promise<void>;
  fetchCashFlow: () => Promise<void>;
  addTransaction: (tx: Partial<LedgerTransaction>) => Promise<void>;
  submitJournalReview: (review: Partial<JournalEntry>) => Promise<void>;
  uploadScreenshot: (tradeId: string, file: File) => Promise<string>;
}

export const useLedgerStore = create<LedgerState>((set, get) => ({
  transactions: [],
  cashFlow: null,
  isLoading: false,
  error: null,

  fetchTransactions: async () => {
    set({ isLoading: true });
    try {
      const res = await fetch('/api/personal/transactions');
      const data = await res.json();
      set({ transactions: data, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  fetchCashFlow: async () => {
    try {
      const res = await fetch('/api/personal/cash-flow');
      const data = await res.json();
      set({ cashFlow: data });
    } catch (err: any) {
      console.error(err);
    }
  },

  addTransaction: async (tx) => {
    await fetch('/api/personal/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tx),
    });
    await get().fetchTransactions();
    await get().fetchCashFlow();
  },

  submitJournalReview: async (review) => {
    await fetch('/api/journal/review', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(review),
    });
  },

  uploadScreenshot: async (tradeId: string, file: File) => {
    const formData = new FormData();
    formData.append('trade_id', tradeId);
    formData.append('file', file);

    const res = await fetch('/api/journal/screenshot', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    return data.saved_path;
  },
}));