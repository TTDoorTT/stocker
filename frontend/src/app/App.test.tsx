import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { Stock } from '../features/market/types';
import type { Run } from '../features/research/types';
import type { Evidence } from '../shared/types';
import { App } from './App';

const timestamp = '2025-01-01T00:00:00Z';
const evidence: Evidence = {
  evidence_id: 'ev-test',
  symbol: 'AAPL',
  field: 'revenue',
  value: 100,
  unit: 'USD',
  currency: 'USD',
  period: 'FY2024',
  source_name: 'Synthetic test fixture',
  source_url: 'https://example.org/fixture',
  published_at: timestamp,
  fetched_at: timestamp,
  fixture: true,
};
const stock: Stock = {
  symbol: 'AAPL',
  name: 'Apple fixture',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  profile: 'Synthetic test company profile',
  quote: {
    price: 100,
    previous_close: 90,
    timestamp,
    source_name: 'Synthetic test fixture',
    source_url: 'https://example.org/fixture',
    stale: true,
    delayed: true,
  },
  facts: [evidence],
  news: [],
  gaps: ['Consensus unavailable'],
  evidence: [evidence],
};
const run: Run = {
  run_id: 'test-run',
  symbol: 'AAPL',
  status: 'incomplete',
  model_id: 'fixture-stub',
  mode: 'fixtures',
  started_at: timestamp,
  stages: [
    {
      stage: 'profile',
      attempt: 1,
      status: 'complete',
      input_evidence_ids: ['ev-test'],
      validation_errors: [],
      output: { summary: 'Identity verified from test fixture' },
    },
  ],
  evidence: [evidence],
  calculations: [],
  report: '# Saved fixture report\n\nEducational synthetic output.',
  gaps: ['Consensus unavailable'],
};
let watches: { symbol: string }[];
let positions: unknown[];
let currentRun: typeof run;
let existingRuns: (typeof run)[] = [];
let healthMode = 'fixtures';
let liveNews = false;
let summaryUnavailable = false;
let dailyNews: {
  headline: string;
  source_name: string;
  source_url: string;
  published_at: string;
  fetched_at: string;
}[] = [];
let currentStock = stock;
let calls: { path: string; method: string; body: unknown }[];
function mount(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}
beforeEach(() => {
  watches = [];
  positions = [];
  calls = [];
  currentRun = { ...run };
  existingRuns = [run];
  healthMode = 'fixtures';
  liveNews = false;
  summaryUnavailable = false;
  dailyNews = [];
  currentStock = { ...stock };
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: string, options?: RequestInit) => {
      const path = String(input).replace('/api', '');
      const method = options?.method || 'GET';
      const body = options?.body ? JSON.parse(String(options.body)) : null;
      calls.push({ path, method, body });
      let response: unknown = {};
      let status = 200;
      if (path === '/settings/ai')
        response = {
          base_url: 'http://127.0.0.1:4000/v1',
          model_id: 'configured-test',
          configured: true,
          has_api_key: false,
          source: 'environment',
        };
      else if (path === '/health')
        response = { status: 'ok', mode: healthMode, model_id: 'fixture-stub', model_configured: false };
      else if (path === '/markets/overview') response = [];
      else if (path === '/daily-review')
        response = {
          mode: healthMode,
          as_of: timestamp,
          proxies: [
            {
              symbol: 'SPY',
              name: 'SPDR S&P 500 ETF Trust',
              quote: stock.quote,
              daily_return_pct: 1.25,
              gaps: [],
            },
            {
              symbol: 'QQQ',
              name: 'Invesco QQQ Trust',
              quote: stock.quote,
              daily_return_pct: -0.5,
              gaps: [],
            },
          ],
          news: dailyNews,
          coverage: 'SPY and QQQ ETF proxies; no market-wide breadth',
          session: 'Market session is not inferred; use individual quote timestamps.',
          gaps: ['ETF prices are not index levels.'],
        };
      else if (path.startsWith('/stocks/search')) {
        const q = new URL(path, 'http://localhost').searchParams.get('q')?.toUpperCase() || '';
        response = q.includes('MSFT')
          ? [{ symbol: 'MSFT', name: 'Microsoft fixture' }]
          : [{ symbol: 'AAPL', name: 'Apple fixture' }];
      } else if (path === '/stocks/AAPL') response = currentStock;
      else if (path === '/stocks/MSFT')
        response = { ...currentStock, symbol: 'MSFT', name: 'Microsoft fixture' };
      else if (path.startsWith('/stocks/AAPL/history'))
        response = [
          { date: '2024-12-01', close: 90 },
          { date: '2025-01-01', close: 100 },
        ];
      else if (path === '/watchlist' && method === 'POST') {
        watches.push(body);
        response = body;
      } else if (path.startsWith('/watchlist/') && method === 'DELETE') {
        watches = [];
        response = { deleted: true };
      } else if (path === '/watchlist') response = watches;
      else if (path === '/positions' && method === 'POST') {
        positions.push({ ...body, id: 1, quote_price: 100, unrealized_pnl: 20, mode: 'fixtures' });
        response = { saved: true };
      } else if (path === '/positions') response = positions;
      else if (path === '/research-runs' && method === 'POST') response = currentRun;
      else if (path === '/research-runs/test-run' && method === 'DELETE') {
        existingRuns = existingRuns.filter((item) => item.run_id !== 'test-run');
        response = { deleted: true, run_id: 'test-run' };
      } else if (path === '/research-runs/test-run/cancel' && method === 'POST') {
        currentRun = {
          ...currentRun,
          status: 'cancelled',
          report: null,
          gaps: ['Research run was stopped by the user.'],
        };
        response = currentRun;
      } else if (path === '/research-runs') response = existingRuns;
      else if (path === '/research-runs/test-run') response = currentRun;
      else if (path === '/research-runs/test-run/events')
        response = [
          {
            id: 1,
            event: 'validation_failed',
            stage: 'financials',
            at: timestamp,
            errors: ['Calculation mismatch'],
          },
        ];
      else if (path.startsWith('/intelligence/rss?')) {
        if (!liveNews) {
          status = 503;
          response = { detail: 'Test provider unavailable' };
        } else {
          const selectedCategory = new URL(path, 'http://localhost').searchParams.get('category') || 'ai';

          response = {
            category: selectedCategory,
            categories: [
              { key: 'ai', name: 'AI / LLMs', count: 1 },
              { key: 'semi', name: 'Semiconductors', count: 0 },
            ],
            items: [
              {
                headline: 'Sourced test headline',
                source_url: 'https://example.org/news',
                source_name: 'Test source',
                published_at: timestamp,
                fetched_at: timestamp,
              },
            ],
            sources_total: 88,
            sources_ok: 1,
            sources_failed: 0,
            last_refreshed: timestamp,
            refreshing: false,
            error: '',
          };
        }
      } else if (path === '/intelligence/rss/highlights' && method === 'POST') {
        if (summaryUnavailable) {
          status = 503;
          response = { detail: 'Live model not configured' };
        } else {
          response = {
            answer: 'Sourced RSS industry highlights.',
            evidence: [evidence],
            mode: 'live',
            gaps: ['Full article text unavailable'],
          };
        }
      } else if (path === '/chat')
        response = {
          answer: 'Available test evidence [ev-test].',
          evidence: [evidence],
          mode: 'fixtures',
          gaps: [],
        };
      else {
        status = 503;
        response = { detail: 'Test provider unavailable' };
      }
      return { ok: status < 400, status, json: async () => response } as Response;
    }),
  );
});
describe('Stocker flows', () => {
  it('combines market overview and compact headlines on Home without simple positions or topbar search', async () => {
    positions = [
      {
        id: 1,
        symbol: 'AAPL',
        shares: 2,
        average_cost: 90,
        currency: 'USD',
        quote_price: 100,
        unrealized_pnl: 20,
        mode: 'fixtures',
        quote: stock.quote,
      },
    ];
    dailyNews = Array.from({ length: 6 }, (_, i) => ({
      headline: `Daily market headline ${i + 1}`,
      source_name: 'Test wire',
      source_url: `https://example.org/headline-${i + 1}`,
      published_at: timestamp,
      fetched_at: timestamp,
    }));
    mount('/');
    expect(screen.getByRole('heading', { name: 'Market overview' })).toBeInTheDocument();
    expect(screen.queryByText('A clearer view.')).not.toBeInTheDocument();
    expect(await screen.findByText('+1.25% daily return')).toBeInTheDocument();
    const heatmapHeading = screen.getByRole('heading', { name: 'U.S. stock heatmap' });
    const topNewsHeading = screen.getByRole('heading', { name: 'Top News' });
    expect(
      heatmapHeading.compareDocumentPosition(topNewsHeading) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByRole('link', { name: /Daily market headline 1/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Daily market headline 5/ })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Daily market headline 6/ })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Show all (6)' }));
    expect(screen.getByRole('link', { name: /Daily market headline 6/ })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Simple positions' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Analyze' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('textbox', { name: 'Search U.S. and Canadian stocks' }),
    ).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Daily Review' })).not.toBeInTheDocument();
  });
  it('redirects legacy /daily-review route to Home', async () => {
    mount('/daily-review');
    expect(await screen.findByRole('heading', { name: 'Market workspace' })).toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'Top News' })).toBeInTheDocument();
  });
  it('toggles light and dark themes and restores the saved choice', () => {
    window.localStorage.removeItem('stocker-theme');
    const view = mount('/');
    fireEvent.click(screen.getByRole('button', { name: 'Switch to light theme' }));
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(window.localStorage.getItem('stocker-theme')).toBe('light');
    view.unmount();
    mount('/research');
    fireEvent.click(screen.getByRole('button', { name: 'Switch to dark theme' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    window.localStorage.removeItem('stocker-theme');
  });
  it('shows simplified stock research search with saved stocks and opens stock via Search button', async () => {
    watches = [{ symbol: 'AAPL' }];
    mount('/research');
    expect(screen.getByRole('link', { name: /Stocker RESEARCH WORKSPACE/ })).toBeInTheDocument();
    expect(screen.getByText('STOCKER / U.S. MARKETS')).toBeInTheDocument();
    expect(screen.getByText(/Stocker · U.S. \/ Canadian research workspace/)).toBeInTheDocument();
    expect(await screen.findByText('Demo · synthetic fixtures')).toBeInTheDocument();
    expect(screen.queryByText(/From source to/)).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Analyze' })).not.toBeInTheDocument();
    expect(await screen.findByRole('heading', { name: 'My saved stocks' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'AAPL ↗' })).toBeInTheDocument();
    fireEvent.change(screen.getByRole('textbox', { name: 'Search U.S. and Canadian stocks' }), {
      target: { value: 'AAPL' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByRole('heading', { name: 'Apple fixture' })).toBeInTheDocument();
    expect(await screen.findByText('Consensus unavailable')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Run Research/ })).not.toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Research' })).toHaveAttribute('aria-selected', 'false');
    // Quarterly financial trends appears directly after Price history; Earnings and Event Study are removed.
    const priceHeading = screen.getByRole('heading', { name: /Price history/ });
    const quarterlyHeading = screen.getByRole('heading', { name: 'Quarterly financial trends' });
    expect(
      priceHeading.compareDocumentPosition(quarterlyHeading) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.queryByRole('heading', { name: /Earnings/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Historical event study' })).not.toBeInTheDocument();
    // Quick stock switcher jumps directly to another stock from the stock page.
    fireEvent.change(screen.getByRole('textbox', { name: 'Jump to another stock' }), {
      target: { value: 'MSFT' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Search' }));
    expect(await screen.findByRole('heading', { name: 'Microsoft fixture' })).toBeInTheDocument();
  });
  it('searches stocks and opens matching company from suggestions', async () => {
    mount('/research');
    fireEvent.change(screen.getByRole('textbox', { name: 'Search U.S. and Canadian stocks' }), {
      target: { value: 'Apple' },
    });
    const result = await screen.findByRole('link', { name: /AAPL Apple fixture/ });
    fireEvent.click(result);
    expect(await screen.findByRole('heading', { name: 'Apple fixture' })).toBeInTheDocument();
  });
  it('opens Research tab inline without auto-running, supports Quick/Deep mode selection, starting and stopping', async () => {
    existingRuns = [];
    currentRun = { ...run, status: 'running', report: null };
    mount('/stocks/AAPL');
    expect(await screen.findByRole('heading', { name: 'Apple fixture' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('tab', { name: 'Research' }));
    // Stays on stock page with name/price visible and does NOT start a run automatically.
    expect(screen.getByRole('heading', { name: 'Apple fixture' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Run Deep Research' })).toBeEnabled();
    expect(calls.filter((call) => call.path === '/research-runs' && call.method === 'POST')).toHaveLength(0);

    fireEvent.change(screen.getByRole('combobox', { name: 'Research mode' }), {
      target: { value: 'single' },
    });
    expect(screen.getByRole('option', { name: /Deep Research.*~8–12 min/ })).toBeInTheDocument();
    expect(screen.getByRole('option', { name: /Quick Research.*~1–3 min/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run Quick Research' })).toBeEnabled();
    fireEvent.click(screen.getByRole('button', { name: 'Run Quick Research' }));
    expect(await screen.findByRole('button', { name: 'Stop Research' })).toBeEnabled();
    expect(calls.some((call) => call.path === '/research-runs' && call.method === 'POST')).toBe(true);

    fireEvent.click(screen.getByRole('button', { name: 'Stop Research' }));
    expect(await screen.findByText(/This research run was stopped before completion/)).toBeInTheDocument();
    expect(
      calls.some((call) => call.path === '/research-runs/test-run/cancel' && call.method === 'POST'),
    ).toBe(true);
  });
  it('keeps chat isolated from full research and shows cited answer', async () => {
    mount('/stocks/AAPL');
    fireEvent.change(await screen.findByRole('textbox', { name: 'Stock question' }), {
      target: { value: 'What evidence is available?' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Ask question' }));
    expect(await screen.findByText('Available test evidence [ev-test].')).toBeInTheDocument();
    expect(calls.filter((call) => call.method === 'POST' && call.path === '/research-runs')).toHaveLength(0);
  });
  it('adds watchlist entry and removes it through My Stocks without simple positions', async () => {
    mount('/stocks/AAPL');
    fireEvent.click(await screen.findByRole('button', { name: '+ Watchlist' }));
    expect(await screen.findByText('AAPL added to watchlist')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('link', { name: 'My Stocks' }));
    const remove = await screen.findByRole('button', { name: 'Remove AAPL from watchlist' });
    expect(screen.queryByRole('heading', { name: 'Simple positions' })).not.toBeInTheDocument();
    fireEvent.click(remove);
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Remove AAPL from watchlist' })).not.toBeInTheDocument(),
    );
  });
  it('shows real running state then polls the saved terminal report', async () => {
    currentRun = { ...run, status: 'running', report: null };
    mount('/runs/test-run');
    expect(await screen.findByText(/Agents are executing/)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Saved fixture report' })).not.toBeInTheDocument();
    currentRun = { ...run };
    expect(
      await screen.findByRole('heading', { name: 'Saved fixture report' }, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(calls.filter((call) => call.path === '/research-runs/test-run')).toHaveLength(2);
  });
  it('shows failed runs without inventing a report', async () => {
    currentRun = { ...run, status: 'failed', report: null };
    mount('/runs/test-run');
    expect(await screen.findByText(/A report is unavailable for this run/)).toBeInTheDocument();
    expect(screen.getByText('failed')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Download Markdown ↓' })).not.toBeInTheDocument();
  });
  it('keeps live mode separate and handles unknown publication dates', async () => {
    healthMode = 'live';
    currentStock = {
      ...stock,
      facts: [{ ...evidence, published_at: null, currency: null, source_url: 'fixture:market.json' }],
    };
    mount('/stocks/AAPL');
    expect(await screen.findByText(/Facts are returned by configured providers/)).toBeInTheDocument();
    expect(await screen.findAllByText('Unavailable')).not.toHaveLength(0);
    expect(document.querySelector('a[href^="fixture:"]')).toBeNull();
  });

  it('generates RSS highlights only on explicit request', async () => {
    liveNews = true;
    mount('/intelligence');

    const article = await screen.findByRole('link', {
      name: 'Sourced test headline',
    });

    expect(article).toHaveAttribute('href', 'https://example.org/news');

    // Loading the news must never invoke the LLM.
    expect(calls.filter((call) => call.path === '/intelligence/rss/highlights')).toHaveLength(0);

    fireEvent.click(
      screen.getByRole('button', {
        name: 'Generate AI highlights',
      }),
    );

    expect(await screen.findByText('Sourced RSS industry highlights.')).toBeInTheDocument();

    expect(screen.getByText('Full article text unavailable')).toBeInTheDocument();

    expect(
      calls.filter((call) => call.path === '/intelligence/rss/highlights' && call.method === 'POST'),
    ).toEqual([
      {
        path: '/intelligence/rss/highlights',
        method: 'POST',
        body: { category: 'ai' },
      },
    ]);

    expect(calls.filter((call) => call.path === '/research-runs' && call.method === 'POST')).toHaveLength(0);
  });

  it('reports missing AI configuration without inventing highlights', async () => {
    liveNews = true;
    summaryUnavailable = true;

    mount('/intelligence');

    fireEvent.click(
      await screen.findByRole('button', {
        name: 'Generate AI highlights',
      }),
    );

    expect(await screen.findByText('Live model not configured')).toBeInTheDocument();

    expect(screen.queryByText('Sourced RSS industry highlights.')).not.toBeInTheDocument();
  });

  it('reopens a saved report and reports RSS provider failures', async () => {
    mount('/records');

    expect(await screen.findByRole('button', { name: 'Delete AAPL research record' })).toBeEnabled();

    fireEvent.click(
      screen.getByRole('link', {
        name: 'Open analysis ↗',
      }),
    );

    expect(
      await screen.findByRole('heading', {
        name: 'Saved fixture report',
      }),
    ).toBeInTheDocument();

    fireEvent.click(
      screen.getByRole('link', {
        name: 'Industry Intelligence',
      }),
    );

    expect(await screen.findByText('Test provider unavailable')).toBeInTheDocument();

    expect(calls.some((call) => call.path.startsWith('/intelligence/rss?'))).toBe(true);
  });

  it('deletes a saved research record from Research Records', async () => {
    mount('/records');
    const del = await screen.findByRole('button', { name: 'Delete AAPL research record' });
    fireEvent.click(del);
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Delete AAPL research record' })).not.toBeInTheDocument(),
    );
    expect(calls.some((call) => call.path === '/research-runs/test-run' && call.method === 'DELETE')).toBe(
      true,
    );
  });

  it('allows hiding and restoring Industry Research in Settings', () => {
    window.localStorage.removeItem('stocker-hide-industry-research');
    const view = mount('/settings');
    expect(screen.getByRole('link', { name: 'Industry Research' })).toBeInTheDocument();
    const toggle = screen.getByRole('checkbox', { name: 'Hide Industry Research from workspace sidebar' });
    fireEvent.click(toggle);
    expect(screen.queryByRole('link', { name: 'Industry Research' })).not.toBeInTheDocument();
    view.unmount();

    const reloaded = mount('/');
    expect(screen.queryByRole('link', { name: 'Industry Research' })).not.toBeInTheDocument();
    reloaded.unmount();

    mount('/settings');
    fireEvent.click(screen.getByRole('checkbox', { name: 'Hide Industry Research from workspace sidebar' }));
    expect(screen.getByRole('link', { name: 'Industry Research' })).toBeInTheDocument();
    window.localStorage.removeItem('stocker-hide-industry-research');
  });
});
