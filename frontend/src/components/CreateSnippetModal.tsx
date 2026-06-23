import { useState } from 'react';
import { API } from '../constants';
import { type Snippet } from './CodeSnippet';
import { FormField } from './FormField';
import { LanguageSelect } from './LanguageSelect';
import { authHeaders } from '../utils/auth';

const EMPTY_FORM = { title: '', language: '', code: '', description: '', tags: '' };

type Tab = 'manual' | 'ai';

interface Props {
  token: string;
  onClose: () => void;
  onCreate: (snippet: Snippet) => void;
}

export default function CreateSnippetModal({ token, onClose, onCreate }: Props) {
  const [tab, setTab] = useState<Tab>('manual');
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  // AI tab state
  const [aiCode, setAiCode] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [aiError, setAiError] = useState('');
  const [aiFilled, setAiFilled] = useState(false);

  function validate() {
    const errs: Record<string, string> = {};
    if (!form.title.trim()) errs.title = "Title is required";
    if (!form.language.trim()) errs.language = "Language is required";
    if (!form.code.trim()) errs.code = "Code is required";
    return errs;
  }

  function clearError(field: string) {
    setErrors((err) => ({ ...err, [field]: "" }));
  }

  async function handleGenerate() {
    if (!aiCode.trim()) return;
    setAnalyzing(true);
    setAiError('');
    try {
      const res = await fetch(`${API}/snippets/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ code: aiCode }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.detail || `HTTP ${res.status}`);
      }
      const meta = await res.json();
      // Drop everything the model returned — plus the pasted code itself —
      // into the manual form, then switch there so the user reviews and edits
      // before saving. Nothing is saved automatically.
      setForm({
        title: meta.title ?? '',
        language: meta.language ?? '',
        code: aiCode,
        description: meta.description ?? '',
        tags: Array.isArray(meta.tags) ? meta.tags.join(', ') : '',
      });
      setErrors({});
      setAiFilled(true);
      setTab('manual');
    } catch (err) {
      setAiError((err as Error).message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate();
    setErrors(errs);
    if (Object.keys(errs).length > 0) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/snippets/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          title: form.title,
          language: form.language.toUpperCase(),
          code: form.code,
          description: form.description || undefined,
          tags: form.tags.split(',').map((t) => t.trim()).filter(Boolean),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const created: Snippet = await res.json();
      onCreate(created);
    } catch (err) {
      alert((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel" onClick={(e) => e.stopPropagation()}>
        <h2 className="overlay-title">New Snippet</h2>

        <div className="snippet-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'manual'}
            className={`snippet-tab${tab === 'manual' ? ' snippet-tab--active' : ''}`}
            onClick={() => setTab('manual')}
          >
            Manual
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'ai'}
            className={`snippet-tab${tab === 'ai' ? ' snippet-tab--active' : ''}`}
            onClick={() => setTab('ai')}
          >
            ✨ AI
          </button>
        </div>

        {tab === 'ai' ? (
          <div className="overlay-form">
            <p className="snippet-ai-hint">
              Paste your code and let AI fill in the title, language, description, and tags.
              You can review and edit everything before saving.
            </p>
            <textarea
              className="snippet-edit-textarea snippet-edit-code"
              placeholder="Paste your code here…"
              rows={12}
              spellCheck={false}
              value={aiCode}
              onChange={(e) => setAiCode(e.target.value)}
            />
            {aiError && <span className="snippet-ai-hint snippet-ai-hint--error">{aiError}</span>}
            <div className="snippet-edit-actions">
              <button type="button" className="snippet-btn snippet-btn--ghost" onClick={onClose}>
                Cancel
              </button>
              <button
                type="button"
                className="snippet-btn snippet-btn--primary"
                onClick={handleGenerate}
                disabled={analyzing || !aiCode.trim()}
              >
                {analyzing ? 'Generating…' : 'Generate fields'}
              </button>
            </div>
          </div>
        ) : (
          <form className="overlay-form" onSubmit={handleSubmit}>
            {aiFilled && (
              <span className="snippet-ai-hint">Filled by AI — review before saving.</span>
            )}
            <div className="snippet-edit-row">
              <FormField error={errors.title}>
                <input
                  className={`snippet-edit-input${errors.title ? " snippet-edit-input--error" : ""}`}
                  placeholder="Title *"
                  value={form.title}
                  onChange={(e) => {
                    setForm((f) => ({ ...f, title: e.target.value }));
                    clearError("title");
                  }}
                />
              </FormField>
              <FormField error={errors.language} className="snippet-field--lang">
                <LanguageSelect
                  value={form.language}
                  onChange={(lang) => setForm((f) => ({ ...f, language: lang }))}
                  error={errors.language}
                  onClearError={() => clearError("language")}
                />
              </FormField>
            </div>
            <FormField error={errors.code}>
              <textarea
                className={`snippet-edit-textarea snippet-edit-code${errors.code ? " snippet-edit-input--error" : ""}`}
                placeholder="Code *"
                rows={10}
                spellCheck={false}
                value={form.code}
                onChange={(e) => {
                  setForm((f) => ({ ...f, code: e.target.value }));
                  clearError("code");
                }}
              />
            </FormField>
            <textarea
              className="snippet-edit-textarea"
              placeholder="Description (optional)"
              rows={2}
              value={form.description}
              onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
            />
            <input
              className="snippet-edit-input"
              placeholder="Tags (comma separated)"
              value={form.tags}
              onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
            />
            <div className="snippet-edit-actions">
              <button type="button" className="snippet-btn snippet-btn--ghost" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="snippet-btn snippet-btn--primary" disabled={saving}>
                {saving ? 'Saving…' : 'Create'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
