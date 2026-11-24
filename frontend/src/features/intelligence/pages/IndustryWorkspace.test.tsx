import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, expect, it, vi } from 'vitest';
import { intelligenceApi } from '../api';
import { IndustryWorkspace } from './IndustryWorkspace';

vi.mock('../api', () => ({
  intelligenceApi: {
    industry: vi.fn(),
    savedIndustrySection: vi.fn(),
    generateIndustrySection: vi.fn(),
    filingExcerpts: vi.fn(),
  },
  fetchIndustryEvidence: vi.fn(),
}));

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(intelligenceApi.savedIndustrySection).mockResolvedValue({
    industry_slug: 'semiconductor',
    section: 'technology',
    saved: false,
    generated_at: null,
    model_id: null,
    stale: false,
    result: null,
  });
});

it('defaults semiconductor pilot to its first AI-enabled tab and exposes SEC filing excerpts', async () => {
  vi.mocked(intelligenceApi.industry).mockResolvedValue({
    slug: 'semiconductor',
    name: 'Global semiconductor supply chains',
    symbols: ['NVDA'],
    prompt: 'Map semiconductor supply chain.',
    gaps: [],
    research_status: 'limited_pilot',
    ai_sections: ['technology', 'supply-chain', 'competition'],
    research_coverage: 'Limited U.S. SEC 10-K semiconductor filing pilot.',
  });

  render(
    <MemoryRouter initialEntries={['/industries/semiconductor']}>
      <Routes>
        <Route path="/industries/:slug" element={<IndustryWorkspace />} />
      </Routes>
    </MemoryRouter>,
  );

  const techTab = await screen.findByRole('tab', { name: 'Technology · AI' });
  expect(techTab).toHaveAttribute('aria-selected', 'true');
  expect(screen.getByRole('tab', { name: 'Overview' })).toHaveAttribute('aria-selected', 'false');
  expect(screen.getByRole('heading', { name: 'Original SEC 10-K filing excerpts' })).toBeInTheDocument();
  expect(intelligenceApi.filingExcerpts).not.toHaveBeenCalled();
});

it('keeps guided-only industries on Overview without SEC filing excerpts preview', async () => {
  vi.mocked(intelligenceApi.industry).mockResolvedValue({
    slug: 'humanoid',
    name: 'Humanoid robotics',
    symbols: [],
    prompt: 'Examine robotics bottlenecks.',
    gaps: [],
    research_status: 'guided_only',
    ai_sections: [],
    research_coverage: 'Guided research only.',
  });

  render(
    <MemoryRouter initialEntries={['/industries/humanoid']}>
      <Routes>
        <Route path="/industries/:slug" element={<IndustryWorkspace />} />
      </Routes>
    </MemoryRouter>,
  );

  const overviewTab = await screen.findByRole('tab', { name: 'Overview' });
  expect(overviewTab).toHaveAttribute('aria-selected', 'true');
  expect(
    screen.queryByRole('heading', { name: 'Original SEC 10-K filing excerpts' }),
  ).not.toBeInTheDocument();
});
