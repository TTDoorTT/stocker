import { Link } from 'react-router-dom';
import { PageTitle } from '../../../shared/ui/Presentation';

export function ResearchLanding() {
  return (
    <>
      <PageTitle title="Stock research" />
      <section className="hero">
        <div>
          <p className="eyebrow">SIX DISTINCT SPECIALISTS</p>
          <h2>
            From source to
            <br />
            scrutinized report.
          </h2>
          <p>
            Search a U.S. ticker or explicit Canadian .TO / .V listing above or choose a starting symbol
            below. Each run preserves the evidence, calculations and actual agent transitions.
          </p>
          <div className="ticker-links">
            {['AAPL', 'MSFT', 'NVDA'].map((symbol) => (
              <Link key={symbol} to={`/stocks/${symbol}`}>
                {symbol} ↗
              </Link>
            ))}
          </div>
        </div>
        <div className="pipeline-mini">
          {[
            'Company profile',
            'Financial analysis',
            'Sourced expectations',
            'Deterministic valuation',
            'Risk & counterevidence',
            'Evidence-backed report',
          ].map((stage, i) => (
            <div key={stage}>
              <span>0{i + 1}</span>
              {stage}
            </div>
          ))}
        </div>
      </section>
      <div className="notice">
        Missing consensus, provider failures and disputed claims are retained as explicit gaps. Research is
        educational and does not provide investment advice.
      </div>
    </>
  );
}
