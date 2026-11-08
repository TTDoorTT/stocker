import { render, screen, within } from '@testing-library/react';
import { expect, it } from 'vitest';
import type { IssuerFinding } from '../types';
import { IssuerFindings } from './IssuerFindings';

const URL = 'https://www.sec.gov/Archives/edgar/data/1045810/000104581026000001/report.htm';

const findings: IssuerFinding[] = [
  {
    claim_index: 0,
    text: 'AMD describes a specific technical integration approach.',
    issuers: ['AMD'],
    scope: 'single_issuer',
    citations: [{ evidence_id: 'ev-amd', symbol: 'AMD', source_url: URL }],
  },
  {
    claim_index: 1,
    text: 'The selected disclosures discuss different packaging activities.',
    issuers: ['AMD', 'AVGO'],
    scope: 'multiple_issuers',
    citations: [
      { evidence_id: 'ev-amd', symbol: 'AMD', source_url: URL },
      { evidence_id: 'ev-avgo', symbol: 'AVGO', source_url: URL },
    ],
  },
];

it('shows individual issuer findings and SEC citation links', () => {
  render(<IssuerFindings findings={findings} />);

  const region = screen.getByRole('region', { name: 'Issuer-attributed findings' });

  expect(within(region).getByText('AMD')).toBeInTheDocument();
  expect(within(region).getByText(/specific technical integration approach/)).toBeInTheDocument();

  const links = within(region).getAllByRole('link');
  expect(links).toHaveLength(3);
  expect(links[0]).toHaveAttribute('href', URL);
  expect(links[0]).toHaveAttribute('rel', 'noopener noreferrer');
});

it('keeps multi-issuer claims separate from individual findings', () => {
  render(<IssuerFindings findings={findings} />);

  expect(screen.getByText(/Multiple-issuer citations/)).toBeInTheDocument();
  expect(screen.getByText('AMD, AVGO')).toBeInTheDocument();
  expect(screen.getByText(/does not establish relative performance/)).toBeInTheDocument();
});

it('does not render a findings section for legacy reports', () => {
  render(<IssuerFindings />);

  expect(screen.queryByRole('region', { name: 'Issuer-attributed findings' })).toBeNull();
});

it('does not produce an unsafe citation link', () => {
  const unsafe: IssuerFinding[] = [
    {
      ...findings[0],
      citations: [
        {
          evidence_id: 'ev-amd',
          symbol: 'AMD',
          source_url: 'javascript:alert(1)',
        },
      ],
    },
  ];

  render(<IssuerFindings findings={unsafe} />);

  expect(screen.queryByRole('link')).toBeNull();
  expect(screen.getByText('Source link unavailable')).toBeInTheDocument();
});
