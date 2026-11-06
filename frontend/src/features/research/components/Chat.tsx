import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { ErrorBox, Gaps } from '../../../shared/ui/Feedback';
import { ModeBadge } from '../../../shared/ui/Presentation';
import { researchApi } from '../api';
import type { ChatReply } from '../types';

export function Chat({ symbol }: { symbol: string }) {
  const [message, setMessage] = useState('');
  const [answer, setAnswer] = useState<ChatReply>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      setAnswer(await researchApi.chat(symbol, message));
      setMessage('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chat unavailable');
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Ask about {symbol}</h2>
        <span className="badge">Read-only context</span>
      </div>
      <p className="muted">
        Ask a focused question about available sources. Chat does not start a research run.
      </p>
      <form className="chat-form" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-message">
          Stock question
        </label>
        <textarea
          id="chat-message"
          placeholder="What evidence is available about this company’s financial performance?"
          value={message}
          maxLength={2000}
          onChange={(e) => setMessage(e.target.value)}
          required
        />
        <button className="button" disabled={busy || !message.trim()}>
          {busy ? 'Reading sources…' : 'Ask question'}
        </button>
      </form>
      {error && <ErrorBox message={error} />}{' '}
      {answer && (
        <div className="chat-answer">
          <ModeBadge mode={answer.mode} />
          <div className="markdown">
            <ReactMarkdown>{answer.answer}</ReactMarkdown>
          </div>
          <Gaps gaps={answer.gaps} />
          <details>
            <summary>Answer sources</summary>
            <EvidenceTable evidence={answer.evidence} />
          </details>
        </div>
      )}
    </section>
  );
}
