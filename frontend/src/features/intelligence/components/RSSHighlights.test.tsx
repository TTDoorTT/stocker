import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { intelligenceApi } from '../api';
import type { SavedRSSHighlights } from '../types';
import { RSSHighlights } from './RSSHighlights';

vi.mock('../api', () => ({
  intelligenceApi: {
    savedRSSHighlights: vi.fn(),
    rssHighlights: vi.fn(),
  },
}));

const stored: SavedRSSHighlights = {
  category: 'ai',
  saved: true,
  generated_at: '2026-11-06T20:00:00+00:00',
  model_id: 'test-model',
  stale: false,
  result: {
    answer: 'Previously saved AI highlights.',
    evidence: [],
    gaps: [],
    mode: 'live',
  },
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(intelligenceApi.savedRSSHighlights).mockResolvedValue(stored);
});

it('restores a saved category summary without invoking the model', async () => {
  render(<RSSHighlights category="ai" hasNews newsRevision="2026-11-06T19:00:00+00:00" />);
  expect(await screen.findByText('Previously saved AI highlights.')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Regenerate AI highlights' })).toBeEnabled();
  expect(intelligenceApi.rssHighlights).not.toHaveBeenCalled();
});

it('keeps a saved result if regeneration fails', async () => {
  vi.mocked(intelligenceApi.rssHighlights).mockRejectedValue(new Error('Provider unavailable'));
  render(<RSSHighlights category="ai" hasNews newsRevision={null} />);
  await screen.findByText('Previously saved AI highlights.');
  fireEvent.click(screen.getByRole('button', { name: 'Regenerate AI highlights' }));
  expect(await screen.findByText('Provider unavailable')).toBeInTheDocument();
  expect(screen.getByText('Previously saved AI highlights.')).toBeInTheDocument();
});

it('labels changed article selection without removing saved highlights', async () => {
  vi.mocked(intelligenceApi.savedRSSHighlights).mockResolvedValue({ ...stored, stale: true });
  render(<RSSHighlights category="ai" hasNews newsRevision="2026-11-07" />);
  expect(await screen.findByText(/News has changed since these highlights/)).toBeInTheDocument();
  expect(screen.getByText('Previously saved AI highlights.')).toBeInTheDocument();
});

it('preserves an explicit generation error when the earlier cache read fails', async () => {
  let failCache: ((reason?: unknown) => void) | undefined;

  const pending = new Promise<SavedRSSHighlights>((_resolve, reject) => {
    failCache = reject;
  });

  vi.mocked(intelligenceApi.savedRSSHighlights).mockReturnValueOnce(pending);
  vi.mocked(intelligenceApi.rssHighlights).mockRejectedValue(new Error('Live model not configured'));

  render(<RSSHighlights category="ai" hasNews newsRevision={null} />);

  fireEvent.click(screen.getByRole('button', { name: 'Generate AI highlights' }));
  expect(await screen.findByText('Live model not configured')).toBeInTheDocument();

  await act(async () => {
    failCache?.(new Error('Cache read unavailable'));
  });

  expect(screen.getByText('Live model not configured')).toBeInTheDocument();
  expect(screen.queryByText('Saved highlights are temporarily unavailable.')).toBeNull();
});
