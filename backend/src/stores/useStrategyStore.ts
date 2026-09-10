import { create } from 'zustand';

export interface StrategyVersion {
  id: string;
  version_name: string;
  win_rate: number;
  profit_factor: number;
  max_drawdown: number;
  net_profit: number;
  sharpe_ratio: number;
  created_at: string;
}

export interface MonteCarloSimulation {
  iterations: number;
  confidence_95_drawdown: number;
  ruin_probability: number;
  median_final_equity: number;
  simulated_curves: number[][];
}

interface StrategyState {
  versions: StrategyVersion[];
  selectedVersion: StrategyVersion | null;
  monteCarloResult: MonteCarloSimulation | null;
  isLoading: boolean;
  error: string | null;
  fetchVersions: () => Promise<void>;
  selectVersion: (version: StrategyVersion) => void;
  runMonteCarlo: (versionId: string, iterations?: number) => Promise<void>;
}

export const useStrategyStore = create<StrategyState>((set) => ({
  versions: [],
  selectedVersion: null,
  monteCarloResult: null,
  isLoading: false,
  error: null,

  fetchVersions: async () => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch('/api/strategies/versions');
      const data = await res.json();
      set({ versions: data, selectedVersion: data[0] || null, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },

  selectVersion: (version) => set({ selectedVersion: version }),

  runMonteCarlo: async (versionId: string, iterations = 1000) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`/api/analytics/monte-carlo`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ version_id: versionId, iterations }),
      });
      const data = await res.json();
      set({ monteCarloResult: data, isLoading: false });
    } catch (err: any) {
      set({ error: err.message, isLoading: false });
    }
  },
}));