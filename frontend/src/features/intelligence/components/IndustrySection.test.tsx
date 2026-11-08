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
