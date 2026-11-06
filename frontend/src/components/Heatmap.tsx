import { useEffect, useRef, useState } from 'react';

type WidgetStatus = 'loading' | 'loaded' | 'failed';
const messageType = 'stockscope-heatmap-status';

function widgetDocument(attempt: number) {
  const config = {
    exchanges: [],
    dataSource: 'SPX500',
    grouping: 'sector',
    blockSize: 'market_cap_basic',
    blockColor: 'change',
    locale: 'en',
    symbolUrl: '',
    colorTheme: 'dark',
    hasTopBar: true,
    isDataSetEnabled: true,
    isZoomEnabled: true,
    hasSymbolTooltip: true,
    isMonoSize: false,
    width: '100%',
    height: 440,
  };
  // A data URL keeps this wrapper opaque even when the provider needs its own origin.
  // The official script owns only this disposable document, never React's DOM.
  return `<!doctype html><html lang="en"><head><meta charset="UTF-8"><style>
    html,body{margin:0;width:100%;height:100%;background:#101824} .tradingview-widget-container{height:100%;width:100%}
    </style></head><body><div id="widget" class="tradingview-widget-container">
    <div class="tradingview-widget-container__widget"></div></div><script>
    const notify = status => parent.postMessage({type:${JSON.stringify(messageType)},attempt:${attempt},status}, '*');
    const container = document.getElementById('widget');
    const seen = new WeakSet();
    const observer = new MutationObserver(() => {
      container.querySelectorAll('iframe').forEach(frame => {
        if (seen.has(frame)) return;
        seen.add(frame);
        frame.title = 'TradingView U.S. stock heatmap';
        frame.addEventListener('load', () => notify('loaded'), {once:true});
      });
    });
    observer.observe(container, {childList:true,subtree:true});
    const script = document.createElement('script');
    script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-stock-heatmap.js';
    script.async = true;
    script.textContent = ${JSON.stringify(JSON.stringify(config))};
    script.onerror = () => notify('failed');
    container.appendChild(script);
    window.addEventListener('pagehide', () => observer.disconnect(), {once:true});
    </script></body></html>`;
}

/** Isolated official widget; its display data is never read by the application. */
export function Heatmap() {
  const frame = useRef<HTMLIFrameElement>(null);
  const [attempt, setAttempt] = useState(0);
  const [status, setStatus] = useState<WidgetStatus>('loading');

  useEffect(() => {
    setStatus('loading');
    const receive = (event: MessageEvent) => {
      if (
        event.source !== frame.current?.contentWindow ||
        event.data?.type !== messageType ||
        event.data.attempt !== attempt
      )
        return;
      if (event.data.status === 'loaded' || event.data.status === 'failed') setStatus(event.data.status);
    };
    window.addEventListener('message', receive);
    const timeout = setTimeout(
      () => setStatus((current) => (current === 'loading' ? 'failed' : current)),
      20000,
    );
    return () => {
      window.removeEventListener('message', receive);
      clearTimeout(timeout);
    };
  }, [attempt]);

  return (
    <section className="panel heatmap">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">VISUAL MARKET CONTEXT</p>
          <h2>U.S. stock heatmap</h2>
        </div>
        <span className="badge">Third-party data</span>
      </div>
      <p className="muted">
        TradingView data is independent of application data and may be delayed. Use the search above to open
        local research.
      </p>
      {status === 'failed' && (
        <div role="status" className="notice">
          The external heatmap could not be confirmed loaded. Network access or browser blocking may affect
          it.{' '}
          <button className="link-button" onClick={() => setAttempt((a) => a + 1)}>
            Reload heatmap
          </button>
        </div>
      )}
      <iframe
        key={attempt}
        ref={frame}
        title="TradingView heatmap sandbox"
        className="heatmap-frame"
        style={{ width: '100%', height: 440, border: 0 }}
        sandbox="allow-scripts allow-same-origin"
        src={`data:text/html;charset=utf-8,${encodeURIComponent(widgetDocument(attempt))}`}
      />
      <a
        className="attribution"
        href="https://www.tradingview.com/heatmap/stock/"
        target="_blank"
        rel="noreferrer"
      >
        Track U.S. markets on TradingView ↗
      </a>
    </section>
  );
}
