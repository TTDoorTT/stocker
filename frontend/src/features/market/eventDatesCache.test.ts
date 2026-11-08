import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApi } from './api';
import type { EventsResponse } from './types';

const { requestMock } = vi.hoisted(() => ({
  requestMock: vi.fn(),
}));

vi.mock('../../shared/api/client', () => ({
  request: requestMock,
}));

const response = (symbol: string): EventsResponse => ({
  symbol,
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  events: [],
  sources: [],
  gaps: [],
});

beforeEach(() => requestMock.mockReset());

describe('shared event-date request', () => {
  it('deduplicates requests for the same listing across the chart and study', async () => {
    requestMock.mockResolvedValue(response('AAPL'));
    const first = marketApi.events('AAPL');
    const second = marketApi.events('aapl');
    expect(first).toBe(second);
    expect(requestMock).toHaveBeenCalledTimes(1);
    expect(await second).toMatchObject({ symbol: 'AAPL' });
  });

  it("does not use another ticker's events", async () => {
    requestMock.mockResolvedValueOnce(response('MSFT')).mockResolvedValueOnce(response('NVDA'));
    const first = await marketApi.events('MSFT');
    const second = await marketApi.events('NVDA');
    expect(first.symbol).toBe('MSFT');
    expect(second.symbol).toBe('NVDA');
    expect(requestMock).toHaveBeenCalledTimes(2);
  });

  it('evicts failures so explicit retry can retrieve dates', async () => {
    requestMock.mockRejectedValueOnce(new Error('Unavailable')).mockResolvedValue(response('TSLA'));
    await expect(marketApi.events('TSLA')).rejects.toThrow('Unavailable');
    await expect(marketApi.events('TSLA')).resolves.toMatchObject({ symbol: 'TSLA' });
    expect(requestMock).toHaveBeenCalledTimes(2);
  });
});
