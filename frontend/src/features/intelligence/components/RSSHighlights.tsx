import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { ErrorBox, Gaps } from '../../../shared/ui/Feedback';
import { dateTime } from '../../../shared/utils/format';
import { intelligenceApi } from '../api';
import type { SavedRSSHighlights } from '../types';

interface Props {
  category: string;
  hasNews: boolean;
  newsRevision: string | null;
}

export function RSSHighlights({ category, hasNews, newsRevision }: Props) {
  const [saved, setSaved] = useState<SavedRSSHighlights>();
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  // A read-only request. It never calls the AI model.
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    void intelligenceApi
      .savedRSSHighlights(category)
      .then((result) => {
        if (!cancelled) {
          setSaved(result);
          setError('');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError((current) => current || 'Saved highlights are temporarily unavailable.');
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [category, newsRevision]);

  async function generate() {
    setGenerating(true);
    setError('');
    try {
      const created = await intelligenceApi.rssHighlights(category);
      try {
        const persisted = await intelligenceApi.savedRSSHighlights(category);
        if (mounted.current) setSaved(persisted);
      } catch {
        // The POST succeeded; keep the new result visible even if the
        // follow-up cache read fails. A later visit will retry the read.
        if (mounted.current) {
          setSaved({
            category,
            saved: true,
            generated_at: null,
            model_id: null,
            stale: false,
            result: created,
          });
        }
      }
    } catch (err) {
      if (mounted.current) {
        setError(err instanceof Error ? err.message : 'AI highlights unavailable');
      }
    } finally {
      if (mounted.current) setGenerating(false);
    }
  }

  return (
    <>
      <div className="rss-highlights">
        <div>
          <h3>Industry highlights</h3>
          <small>Generate from headlines and RSS excerpts. Full articles are not retrieved.</small>
          {saved?.saved && (
            <p className="muted" style={{ margin: '6px 0 0', fontSize: '0.85rem' }}>
              Saved{saved.generated_at ? ` ${dateTime(saved.generated_at)}` : ''}
              {saved.model_id ? ` · ${saved.model_id}` : ''}
            </p>
          )}
          {saved?.stale && (
            <p className="muted" role="status" style={{ margin: '5px 0 0', fontSize: '0.85rem' }}>
              News has changed since these highlights were generated. Regenerate to update them.
            </p>
          )}
        </div>
        <button
          type="button"
          className="button"
          disabled={generating || !hasNews}
          onClick={() => void generate()}
        >
          {generating ? 'Generating…' : saved?.saved ? 'Regenerate AI highlights' : 'Generate AI highlights'}
        </button>
      </div>

      {error && <ErrorBox message={error} />}
      {loading && !saved && <small className="muted">Checking saved highlights…</small>}

      {saved?.result && (
        <section className="chat-answer">
          <div className="markdown">
            <ReactMarkdown>{saved.result.answer}</ReactMarkdown>
          </div>
          <Gaps gaps={saved.result.gaps} />
          <details>
            <summary>Supporting news sources</summary>
            <EvidenceTable evidence={saved.result.evidence} />
          </details>
        </section>
      )}
    </>
  );
}
