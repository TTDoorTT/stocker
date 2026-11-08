import type { EChartsOption } from 'echarts';
import { BarChart, CandlestickChart, LineChart, ScatterChart } from 'echarts/charts';
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import * as echarts from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Empty } from '../../../shared/ui/Feedback';
import { SourceLink } from '../../../shared/ui/Presentation';
import { candleRows, movingAverage, visiblePriceDomain, volumeRows } from '../chartMath';
import { alignEarningsMarkers } from '../earningsMarkers';
import type { CandleSeries, EventsResponse } from '../types';

echarts.use([
  BarChart,
  CandlestickChart,
  ScatterChart,
  LineChart,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  CanvasRenderer,
]);

const rise = '#299c7c';
const fall = '#d76877';
const periods = [5, 10, 20, 60] as const;
const maColors = ['#d5b34d', '#8fbe50', '#ae8cdb', '#5a8ac9'];
const number = new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 });
const compact = new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 });

export function CandleChart({
  series,
  eventDates,
}: {
  series: CandleSeries;
  eventDates?: EventsResponse | null;
}) {
  const container = useRef<HTMLDivElement>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const bars = series.bars;
  const [selectedBar, setSelectedBar] = useState<string | null>(null);
  const aligned = useMemo(
    () =>
      alignEarningsMarkers(
        bars,
        series.interval,
        eventDates?.symbol === series.symbol && eventDates.mode === series.mode ? eventDates.events : [],
      ),
    [bars, series.interval, series.symbol, series.mode, eventDates],
  );
  const markers = aligned.markers;
  const selected = markers.find((marker) => marker.candleDate === selectedBar);
  const current = bars[hovered !== null && hovered < bars.length ? hovered : bars.length - 1];

  useEffect(() => {
    const target = container.current;
    if (!target || bars.length < 2) return;

    const dates = bars.map((bar) => bar.date);
    const closes = bars.map((bar) => bar.close);
    const averages = periods.map((period) => movingAverage(closes, period));
    const volumeAvailable = bars.some((bar) => bar.volume !== null);
    const chart = echarts.init(target, undefined, { renderer: 'canvas' });
    const root = document.documentElement;

    const makeOption = (): EChartsOption => {
      const theme = getComputedStyle(root);
      const muted = theme.getPropertyValue('--muted').trim() || '#91a0b5';
      const border = theme.getPropertyValue('--border').trim() || '#24303f';
      const light = root.dataset.theme === 'light';
      const domain = visiblePriceDomain(bars, averages, 0, 100);
      return {
        animation: false,
        backgroundColor: 'transparent',
        legend: {
          top: 4,
          itemWidth: 15,
          itemHeight: 8,
          data: ['Candles', 'MA5', 'MA10', 'MA20', 'MA60', ...(markers.length ? ['Earnings dates'] : [])],
          textStyle: { color: muted, fontSize: 10 },
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'cross', label: { backgroundColor: light ? '#50667d' : '#2e4053' } },
          backgroundColor: light ? '#ffffff' : '#15202d',
          borderColor: border,
          textStyle: { color: light ? '#203144' : '#e2e9f0', fontSize: 11 },
          formatter: (params: unknown) => {
            const items = Array.isArray(params) ? params : [params];
            const point = items[0] as { axisValue?: string } | undefined;
            const index = point?.axisValue ? dates.indexOf(point.axisValue) : -1;
            if (index < 0) return '';
            const bar = bars[index];
            const lines = [
              bar.date,
              `Open ${number.format(bar.open)} | High ${number.format(bar.high)}`,
              `Low ${number.format(bar.low)} | Close ${number.format(bar.close)}`,
              `Volume ${bar.volume === null ? 'Unavailable' : compact.format(bar.volume)}`,
            ];
            if (bar.adjusted_close !== null) {
              lines.push(`Adjusted close ${number.format(bar.adjusted_close)}`);
            }
            const bucket = markers.find((marker) => marker.candleDate === bar.date);
            if (bucket)
              lines.push(`${bucket.events.length} vendor-reported earnings date(s); time unverified`);
            for (const item of items) {
              const entry = item as { seriesName?: string; value?: unknown };
              if (entry.seriesName?.startsWith('MA') && typeof entry.value === 'number') {
                lines.push(`${entry.seriesName} ${number.format(entry.value)}`);
              }
            }
            return lines.join('<br/>');
          },
        },
        axisPointer: { link: [{ xAxisIndex: 'all' }] },
        grid: [
          { left: 64, right: 20, top: 44, height: '57%' },
          { left: 64, right: 20, top: '70%', height: '14%' },
        ],
        xAxis: [
          {
            type: 'category',
            data: dates,
            boundaryGap: true,
            min: 'dataMin',
            max: 'dataMax',
            axisLabel: { show: false },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false },
          },
          {
            type: 'category',
            gridIndex: 1,
            data: dates,
            boundaryGap: true,
            min: 'dataMin',
            max: 'dataMax',
            axisLabel: { color: muted, fontSize: 10, hideOverlap: true },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false },
          },
        ],
        yAxis: [
          {
            type: 'value',
            scale: true,
            min: domain.min,
            max: domain.max,
            splitNumber: 5,
            axisLabel: { color: muted, fontSize: 10, formatter: (value: number) => number.format(value) },
            splitLine: { lineStyle: { color: border, opacity: 0.6 } },
            axisLine: { show: false },
          },
          {
            type: 'value',
            gridIndex: 1,
            min: 0,
            splitNumber: 2,
            axisLabel: { color: muted, fontSize: 9, formatter: (value: number) => compact.format(value) },
            splitLine: { show: false },
            axisLine: { show: false },
          },
        ],
        dataZoom: [
          { type: 'inside', xAxisIndex: [0, 1], start: 0, end: 100 },
          {
            type: 'slider',
            xAxisIndex: [0, 1],
            start: 0,
            end: 100,
            bottom: 7,
            height: 18,
            showDetail: false,
            brushSelect: false,
            borderColor: border,
            textStyle: { color: muted, fontSize: 9 },
            backgroundColor: light ? '#edf2f6' : '#0e1722',
            fillerColor: light ? '#547aab35' : '#698fc73a',
          },
        ],
        series: [
          {
            name: 'Candles',
            type: 'candlestick',
            data: candleRows(bars),
            barMaxWidth: 12,
            barMinWidth: 2,
            itemStyle: { color: rise, color0: fall, borderColor: rise, borderColor0: fall },
          },
          ...periods.map((period, index) => ({
            name: `MA${period}`,
            type: 'line' as const,
            data: averages[index],
            smooth: false,
            showSymbol: false,
            connectNulls: false,
            lineStyle: { color: maColors[index], width: 1.1, opacity: 0.94 },
            itemStyle: { color: maColors[index] },
          })),
          ...(volumeAvailable
            ? [{ name: 'Volume', type: 'bar' as const, xAxisIndex: 1, yAxisIndex: 1, data: volumeRows(bars) }]
            : []),
          ...(markers.length
            ? [
                {
                  name: 'Earnings dates',
                  type: 'scatter' as const,
                  xAxisIndex: 0,
                  yAxisIndex: 0,
                  symbol: 'diamond',
                  symbolSize: 15,
                  z: 10,
                  itemStyle: { color: '#f3c26e', borderColor: '#253445', borderWidth: 1 },
                  data: markers.map((marker) => [marker.candleDate, marker.anchorPrice]),
                },
              ]
            : []),
        ],
      };
    };

    const rescale = () => {
      // Recalculate from the viewport, not the full 5-year history or zero.
      const zooms = chart.getOption().dataZoom as Array<{ start?: number; end?: number }> | undefined;
      const domain = visiblePriceDomain(bars, averages, zooms?.[0]?.start ?? 0, zooms?.[0]?.end ?? 100);
      chart.setOption({ yAxis: [{ min: domain.min, max: domain.max }] });
    };
    chart.setOption(makeOption());
    chart.on('datazoom', rescale);
    chart.on('mousemove', (event: unknown) => {
      const point = event as { dataIndex?: number; seriesName?: string };
      if (point.seriesName === 'Earnings dates') return;
      const index = point.dataIndex;
      if (Number.isInteger(index) && index !== undefined && index >= 0 && index < bars.length) {
        setHovered(index);
      }
    });
    const openMarker = (event: unknown) => {
      const point = event as { seriesName?: string; dataIndex?: number };
      if (point.seriesName !== 'Earnings dates' || point.dataIndex === undefined) return;
      const marker = markers[point.dataIndex];
      if (marker) setSelectedBar(marker.candleDate);
    };
    chart.on('click', openMarker);
    chart.getZr().on('globalout', () => setHovered(null));

    const resize = () => chart.resize();
    let resizeObserver: ResizeObserver | undefined;
    if (typeof ResizeObserver !== 'undefined') {
      resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(target);
    } else {
      window.addEventListener('resize', resize);
    }
    const themeObserver = new MutationObserver(() => {
      // Restore the user's zoom after adapting foreground/grid colors.
      const oldOptions = chart.getOption();
      chart.setOption(makeOption(), true);
      if (oldOptions.dataZoom) chart.setOption({ dataZoom: oldOptions.dataZoom });
      if (oldOptions.legend) chart.setOption({ legend: oldOptions.legend });
      rescale();
    });
    themeObserver.observe(root, { attributes: true, attributeFilter: ['data-theme'] });

    return () => {
      chart.off('datazoom', rescale);
      chart.off('click', openMarker);
      themeObserver.disconnect();
      resizeObserver?.disconnect();
      window.removeEventListener('resize', resize);
      chart.dispose();
    };
  }, [bars, markers]);

  if (bars.length < 2) {
    return <Empty>Historical OHLCV chart requires at least two sourced trading observations.</Empty>;
  }

  return (
    <div className="candle-chart">
      <div className="candle-chart-meta chart-caption">
        <span>
          {series.currency} · {series.interval} · {series.price_basis.replaceAll('_', ' ')}
        </span>
        <span>
          {bars.length} bars · {bars[0].date} – {bars[bars.length - 1].date}
        </span>
      </div>
      {current && (
        <div className="candle-chart-ohlc" aria-label="Selected trading bar">
          <strong>{current.date}</strong>
          <span>
            O <b>{number.format(current.open)}</b>
          </span>
          <span>
            H <b>{number.format(current.high)}</b>
          </span>
          <span>
            L <b>{number.format(current.low)}</b>
          </span>
          <span>
            C{' '}
            <b className={current.close >= current.open ? 'candle-up' : 'candle-down'}>
              {number.format(current.close)}
            </b>
          </span>
          <span>
            Vol <b>{current.volume === null ? 'Unavailable' : compact.format(current.volume)}</b>
          </span>
        </div>
      )}
      <div
        ref={container}
        className="candle-chart-canvas"
        role="img"
        aria-label={`${series.symbol} interactive candlestick chart with moving averages and volume`}
      />
      {markers.length > 0 && (
        <div className="candle-earnings-markers">
          <details>
            <summary>
              Earnings dates on chart ({markers.reduce((sum, marker) => sum + marker.events.length, 0)})
            </summary>
            <div className="candle-earnings-options" role="group" aria-label="Select earnings marker">
              {markers.map((marker) => (
                <button
                  type="button"
                  key={marker.candleDate}
                  aria-pressed={selectedBar === marker.candleDate}
                  onClick={() => setSelectedBar(marker.candleDate)}
                >
                  {marker.events.length > 1 ? `${marker.events.length} dates · ` : ''}
                  {marker.candleDate}
                </button>
              ))}
            </div>
          </details>
          {selected && (
            <div
              className="candle-earnings-detail"
              role="region"
              aria-label="Selected earnings marker details"
            >
              <strong>Earnings date evidence</strong>
              <p className="muted">
                Chart bar: {selected.candleDate} ·{' '}
                {series.interval === '1d'
                  ? 'Exact trading-date match'
                  : 'Weekly/monthly date bucket, not an exact session'}
              </p>
              {selected.events.map((event) => (
                <p key={event.event_id}>
                  {event.fiscal_quarter} FY{event.fiscal_year} · Vendor-reported date {event.event_date} ·{' '}
                  {event.date_precision === 'date_only'
                    ? 'Release time unverified'
                    : 'Source timestamp available'}{' '}
                  · <SourceLink url={event.source.url} name={event.source.name} />
                  {event.source.fixture ? ' · SYNTHETIC' : ''}
                </p>
              ))}
              <small>No intraday or before/after-close timing is inferred from a date-only event.</small>
            </div>
          )}
        </div>
      )}
      {eventDates && (aligned.outsideRange > 0 || aligned.unaligned > 0) && (
        <p className="muted candle-marker-gaps">
          Earnings dates not plotted: {aligned.outsideRange} outside visible history, {aligned.unaligned}{' '}
          without a matching trading bar. Date-only events are never shifted to another trading day.
        </p>
      )}
      <details className="candle-provenance">
        <summary>Data source &amp; price adjustments — {series.source.name}</summary>
        <small className="source-note">
          {series.source.fixture ? (
            <span>{series.source.name} · SYNTHETIC</span>
          ) : (
            <SourceLink url={series.source.url} name={series.source.name} />
          )}{' '}
          · Retrieved {series.source.fetched_at}
          {series.source.cached ? ' · cached' : ''}
        </small>
        <small>{series.adjustment_note}</small>
        {bars.every((bar) => bar.volume === null) && (
          <small>Trading volume unavailable from this source.</small>
        )}
        {series.gaps.map((gap) => (
          <small key={gap}>{gap}</small>
        ))}
      </details>
    </div>
  );
}
