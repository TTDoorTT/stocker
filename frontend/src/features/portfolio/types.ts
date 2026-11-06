import type { Mode, Quote } from '../../shared/types';
export interface Position {
  id: number;
  symbol: string;
  shares: number;
  average_cost: number;
  currency: string;
  quote_price: number | null;
  unrealized_pnl: number | null;
  mode?: Mode;
  quote?: Quote | null;
  gaps?: string[];
}
