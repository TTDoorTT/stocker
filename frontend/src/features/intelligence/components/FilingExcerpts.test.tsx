import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it, vi } from 'vitest';
import { intelligenceApi } from '../api';
import { FilingExcerpts } from './FilingExcerpts';

vi.mock('../api', () => ({
  intelligenceApi: { filingExcerpts: vi.fn() },
}));

it('fetches only on explicit click and links literal SEC excerpt to source', async () => {
  vi.mocked(intelligenceApi.filingExcerpts).mockResolvedValue({
    industry: 'ai-computing',
    year: 2025,
    mode: 'live',
    coverage: 'Selected SEC filings',
    gaps: ['Not an industry-wide report'],
    excerpts: [
      {
        symbol: 'NVDA',
        form: '10-K',
        filed: '2026-04-01',
        matched_term: 'supply chain',
        text: 'The semiconductor supply chain depends on manufacturing partners.',
        source_name: 'SEC EDGAR primary filing',
        source_url: 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm',
        fetched_at: '2026-11-07T00:00:00+00:00',
        cached: false,
      },
    ],
  });
  render(<FilingExcerpts />);
  expect(intelligenceApi.filingExcerpts).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Load SEC filing excerpts' }));
  expect(await screen.findByText(/The semiconductor supply chain/)).toBeInTheDocument();
  expect(screen.getByRole('link', { name: 'Original SEC filing' })).toHaveAttribute(
    'href',
    'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm',
  );
  expect(intelligenceApi.filingExcerpts).toHaveBeenCalledTimes(1);
});
