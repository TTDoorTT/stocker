import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useResource } from '../../../shared/hooks/useResource';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import type { ChatReply } from '../../research/types';
import { intelligenceApi } from '../api';
import { NewsList } from '../components/NewsList';
import { Signals } from '../components/Signals';
export function NewsRadar() {
  const news = useResource(intelligenceApi.news);
  const [summary, setSummary] = useState<ChatReply>();
  const [summaryError, setSummaryError] = useState('');
  const [summarizing, setSummarizing] = useState(false);
  async function summarize() {
    setSummarizing(true);
    setSummaryError('');
    setSummary(undefined);
    try {
      setSummary(await intelligenceApi.summarizeNews());
    } catch (error) {
      setSummaryError(error instanceof Error ? error.message : 'Headline summary unavailable');
    } finally {
      setSummarizing(false);
    }
  }
  return (
    <>
      <PageTitle title="Industry intelligence" />
      <section className="panel">
        <h2>News radar</h2>
        <p className="muted">
          Headlines and filings remain linked to their original source. Unavailable coverage is shown
          explicitly.
        </p>
        {news.loading ? (
          <Loading />
        ) : news.error ? (
          <ErrorBox message={news.error} retry={news.reload} />
        ) : (
          news.data && (
            <>
              <NewsList items={news.data.items} />
              <Gaps gaps={news.data.gaps} />
              <small>Retrieved {dateTime(news.data.fetched_at)}</small>
              {news.data.mode === 'live' && news.data.items.length > 0 && (
                <div>
                  <p className="muted">
                    Optional AI summary covers retrieved headlines only; full article text is not available.
                  </p>
                  <button className="button secondary" onClick={summarize} disabled={summarizing}>
                    {summarizing ? 'Summarizing sourced headlines…' : 'Summarize headlines'}
                  </button>
                </div>
              )}
            </>
          )
        )}
        {summaryError && <ErrorBox message={summaryError} />}{' '}
        {summary && (
          <section className="chat-answer">
            <h3>Headline-only summary</h3>
            <ModeBadge mode={summary.mode} />
            <div className="markdown">
              <ReactMarkdown>{summary.answer}</ReactMarkdown>
            </div>
            <Gaps gaps={summary.gaps} />
            <details>
              <summary>Summary sources</summary>
              <EvidenceTable evidence={summary.evidence} />
            </details>
          </section>
        )}
      </section>
      <Signals />
    </>
  );
}
