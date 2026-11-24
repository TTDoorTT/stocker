import { useEffect, useRef, useState } from 'react';
import { type AIStatus, appApi } from '../api';

export function AIForm({ initial, onSaved }: { initial: AIStatus; onSaved: (value: AIStatus) => void }) {
  const [baseURL, setBaseURL] = useState(initial.base_url);
  const [model, setModel] = useState(initial.model_id);
  const [key, setKey] = useState('');
  const [noKey, setNoKey] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [tested, setTested] = useState(false);
  const endpointChanged = baseURL.replace(/\/$/, '') !== initial.base_url.replace(/\/$/, '');
  const valid = !!baseURL && !!model && (!endpointChanged || !!key || noKey);
  const change = () => {
    setTested(false);
    setMessage('');
  };
  async function act(action: 'test' | 'save' | 'reset') {
    setBusy(true);
    setMessage('');
    const body = { base_url: baseURL, model_id: model, api_key: noKey ? '' : key || null };
    try {
      if (action === 'test') {
        const result = await appApi.testAI(body);
        setTested(result.ok);
        setMessage(result.message);
      } else {
        const result = action === 'save' ? await appApi.saveAI(body) : await appApi.resetAI();
        setKey('');
        setNoKey(false);
        setTested(false);
        setBaseURL(result.base_url);
        setModel(result.model_id);
        onSaved(result);
        window.dispatchEvent(new Event('ai-configuration-saved'));
        setMessage(
          action === 'save' ? 'Saved. New requests use these settings.' : 'Using environment configuration.',
        );
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Configuration request failed');
    } finally {
      setBusy(false);
    }
  }
  return (
    <form
      className="ai-form"
      onSubmit={(event) => {
        event.preventDefault();
        void act('save');
      }}
      autoComplete="off"
    >
      <fieldset disabled={busy} className="ai-fields">
        <legend className="ai-legend">OpenAI-compatible model connection</legend>
        <div className="ai-input-grid">
          <label className="ai-field">
            <span>API Base URL</span>
            <input
              type="url"
              required
              value={baseURL}
              onChange={(e) => {
                setBaseURL(e.target.value);
                change();
              }}
            />
          </label>
          <label className="ai-field">
            <span>Model ID</span>
            <input
              required
              value={model}
              maxLength={200}
              onChange={(e) => {
                setModel(e.target.value);
                change();
              }}
            />
          </label>
          <label className="ai-field ai-field-full">
            <span>API Key</span>
            <input
              type="password"
              autoComplete="new-password"
              value={key}
              disabled={noKey}
              placeholder={initial.has_api_key ? 'Saved key retained when left blank' : 'Optional'}
              onChange={(e) => {
                setKey(e.target.value);
                change();
              }}
            />
          </label>
        </div>
        <label className="ai-checkbox-row">
          <input
            type="checkbox"
            checked={noKey}
            onChange={(e) => {
              setNoKey(e.target.checked);
              setKey('');
              change();
            }}
          />
          <span>Use no API key (clear saved key)</span>
        </label>
        {endpointChanged && !key && !noKey && (
          <p className="notice">For a changed endpoint, enter its key or select “Use no API key”.</p>
        )}
        <div className="ai-hints">
          <small>
            Docker: use <code>http://host.docker.internal:PORT/v1</code> for a host model. The host service
            must accept container connections. Use HTTPS for remote endpoints.
          </small>
          <small>
            Keys stay on the backend after saving. Saving AI settings does not change synthetic fixture mode
            or financial providers.
          </small>
        </div>
        <div className="actions ai-actions">
          <button
            type="button"
            className="button secondary"
            disabled={!valid}
            onClick={() => void act('test')}
          >
            Test Connection
          </button>
          <button type="submit" className="button" disabled={!valid || !tested}>
            Save
          </button>
          {initial.source === 'saved' && (
            <button type="button" className="button secondary" onClick={() => void act('reset')}>
              Use environment configuration
            </button>
          )}
        </div>
      </fieldset>
      {busy && (
        <p role="status" className="notice">
          Contacting backend…
        </p>
      )}
      {message && (
        <p role="status" className="notice">
          {message}
        </p>
      )}
    </form>
  );
}

export function AISetup() {
  const [config, setConfig] = useState<AIStatus | null>(null);
  const [skipped, setSkipped] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    let active = true;
    appApi
      .ai()
      .then((value) => {
        if (active) setConfig(value);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  const open = !!config && !config.configured && !skipped;
  useEffect(() => {
    if (open) dialog.current?.showModal();
    else if (dialog.current?.open) dialog.current.close();
  }, [open]);
  return (
    <dialog
      ref={dialog}
      className="ai-setup"
      aria-labelledby="ai-setup-title"
      onCancel={() => setSkipped(true)}
    >
      {config && open && (
        <>
          <h2 id="ai-setup-title">Set up AI in Stocker</h2>
          <p className="muted">
            Connect your model, or continue with synthetic fixtures. You can configure AI later in Settings →
            AI.
          </p>
          <AIForm initial={config} onSaved={setConfig} />
          <div className="ai-setup-footer">
            <button type="button" className="button secondary" onClick={() => setSkipped(true)}>
              Skip AI setup
            </button>
          </div>
        </>
      )}
    </dialog>
  );
}
