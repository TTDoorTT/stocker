import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { intelligenceApi } from '../api';
import type { SavedIndustrySection } from '../types';
import { IndustrySection } from './IndustrySection';

vi.mock('../api', () => ({
  intelligenceApi: {
    savedIndustrySection: vi.fn(),
    generateIndustrySection: vi.fn(),
  },
}));

const stored: SavedIndustrySection = {
  industry_slug: 'ai-computing',
  section: 'overview',
  saved: true,
  generated_at: '2026-11-07T06:00:00+00:00',
  model_id: 'test-model',
  stale: false,
  result: { answer: 'Previously captured industry overview.', evidence: [], gaps: [], mode: 'live' },
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue(stored);
});

it('restores saved industry overview without invoking a model', async () => {
  render(<IndustrySection slug="ai-computing" section="overview" enabledSections={['overview']} />);
  expect(await screen.findByText('Previously captured industry overview.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Regenerate Overview' })).toBeEnabled();
  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
});

it('keeps previous research visible when regeneration fails', async () => {
  vi.mocked(intelligenceApi.generateIndustrySection).mockRejectedValue(new Error('Model unavailable'));
  render(<IndustrySection slug="ai-computing" section="overview" enabledSections={['overview']} />);
  await screen.findByText('Previously captured industry overview.');
  fireEvent.click(screen.getByRole('button', { name: 'Regenerate Overview' }));
  expect(await screen.findByText('Model unavailable')).toBeInTheDocument();
  expect(screen.getByText('Previously captured industry overview.')).toBeInTheDocument();
});

it('does not enable unsupported industry sections', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    industry_slug: 'energy',
    section: 'supply-chain',
    saved: false,
    result: null,
  });
  render(<IndustrySection slug="energy" section="supply-chain" enabledSections={[]} />);
  expect(await screen.findByText(/Automated research is not enabled/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Generate Overview/ })).not.toBeInTheDocument();
});

it('enables filing-backed technology generation on explicit click only', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    section: 'technology',
    saved: false,
    result: null,
  });
  vi.mocked(intelligenceApi.generateIndustrySection).mockResolvedValue({
    ...stored,
    section: 'technology',
    result: { answer: 'Source-backed technology note.', evidence: [], gaps: [], mode: 'live' },
  });
  render(<IndustrySection slug="ai-computing" section="technology" enabledSections={['technology']} />);
  const button = await screen.findByRole('button', { name: 'Generate Technology' });
  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
  fireEvent.click(button);
  expect(await screen.findByText('Source-backed technology note.')).toBeInTheDocument();
  expect(intelligenceApi.generateIndustrySection).toHaveBeenCalledWith('ai-computing', 'technology');
});

it('does not enable AI Computing Outlook until sources exist', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    section: 'outlook',
    saved: false,
    result: null,
  });
  render(<IndustrySection slug="ai-computing" section="outlook" enabledSections={[]} />);
  expect(await screen.findByText(/Automated research is not enabled/)).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /Generate Outlook/ })).not.toBeInTheDocument();
});

it('displays filing evidence coverage without treating it as sector coverage', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    section: 'technology',
    result: {
      answer: 'A bounded research note.',
      evidence: [],
      gaps: [],
      mode: 'live',
      filing_coverage: {
        selected_issuers: ['NVDA', 'AMD', 'INTC', 'AVGO', 'MU'],
        represented_issuers: ['NVDA'],
        missing_issuers: ['AMD', 'INTC', 'AVGO', 'MU'],
        accepted_excerpts: 2,
        limitation: 'A limited U.S. issuer sample.',
      },
    },
  });
  render(<IndustrySection slug="ai-computing" section="technology" enabledSections={['technology']} />);
  const summary = await screen.findByLabelText('Filing evidence coverage');
  expect(summary).toHaveTextContent('Accepted excerpts: 2');
  expect(summary).toHaveTextContent('Issuers represented: 1 of 5 selected');
  expect(summary).toHaveTextContent('Missing selected issuers: AMD, INTC, AVGO, MU');
  expect(summary).toHaveTextContent('do not establish industry-wide coverage');
  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
});

it('shows which accepted issuers were cited by model-screened claims', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    section: 'technology',
    result: {
      answer: 'Issuer-limited note.',
      evidence: [],
      gaps: [],
      mode: 'live',
      filing_coverage: {
        selected_issuers: ['NVDA', 'AMD', 'INTC', 'AVGO', 'MU'],
        represented_issuers: ['NVDA', 'AMD', 'MU'],
        missing_issuers: ['INTC', 'AVGO'],
        accepted_excerpts: 4,
        limitation: 'Limited accepted issuer evidence',
        cited_issuers: ['NVDA', 'MU'],
        uncited_represented_issuers: ['AMD'],
        cited_excerpts: 2,
        model_screened_claims: 2,
        citation_limitation: 'Not independent factual verification',
      },
    },
  });
  render(<IndustrySection slug="ai-computing" section="technology" enabledSections={['technology']} />);
  const summary = await screen.findByLabelText('Model-screened claim citation coverage');
  expect(summary).toHaveTextContent('Cited issuers: 2 of 3 represented');
  expect(summary).toHaveTextContent('Distinct cited excerpts: 2');
  expect(summary).toHaveTextContent('Accepted but not cited: AMD');
  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
});

it('prioritizes structured issuer findings without duplicating the narrative', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    section: 'technology',
    result: {
      answer: 'Original research narrative for the saved report.',
      evidence: [],
      gaps: ['Selected issuer disclosures only.', 'Independent verification is unavailable.'],
      mode: 'live',
      issuer_findings: [
        {
          claim_index: 0,
          text: 'AMD describes a specific technical approach.',
          issuers: ['AMD'],
          scope: 'single_issuer',
          citations: [
            {
              evidence_id: 'ev-amd',
              symbol: 'AMD',
              source_url: 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm',
            },
          ],
        },
      ],
    },
  });

  render(<IndustrySection slug="ai-computing" section="technology" enabledSections={['technology']} />);

  expect(await screen.findByRole('region', { name: 'Issuer-attributed findings' })).toBeInTheDocument();

  expect(screen.getByText('AMD describes a specific technical approach.')).toBeInTheDocument();

  const narrative = screen.getByText('Original AI-generated narrative');
  const narrativeDetails = narrative.closest('details');

  expect(narrativeDetails).not.toHaveAttribute('open');

  fireEvent.click(narrative);

  expect(narrativeDetails).toHaveAttribute('open');
  expect(screen.getByText('Original research narrative for the saved report.')).toBeInTheDocument();

  const limitations = screen.getByText(/Data limitations \(2\)/);
  const limitationsDetails = limitations.closest('details');

  expect(limitationsDetails).not.toHaveAttribute('open');

  fireEvent.click(limitations);

  expect(limitationsDetails).toHaveAttribute('open');
  expect(screen.getByText('Independent verification is unavailable.')).toBeInTheDocument();

  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
});

it('keeps legacy research narrative and limitations visible', async () => {
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    ...stored,
    result: {
      answer: 'Original legacy research remains visible.',
      evidence: [],
      gaps: ['Legacy coverage limitation.'],
      mode: 'live',
    },
  });

  render(<IndustrySection slug="ai-computing" section="overview" enabledSections={['overview']} />);

  expect(await screen.findByText('Original legacy research remains visible.')).toBeInTheDocument();

  expect(screen.getByText('Data limitations')).toBeInTheDocument();
  expect(screen.getByText('Legacy coverage limitation.')).toBeInTheDocument();

  expect(screen.queryByText('Original AI-generated narrative')).toBeNull();

  expect(intelligenceApi.generateIndustrySection).not.toHaveBeenCalled();
});
