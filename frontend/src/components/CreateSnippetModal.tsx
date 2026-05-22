import { useState } from 'react';
import { API } from '../constants';
import { type Snippet } from './CodeSnippet';
import { FormField } from './FormField';
import { authHeaders } from '../utils/auth';

const EMPTY_FORM = { title: '', language: '', code: '', description: '', tags: '' };

interface Props {
  token: string;
  onClose: () => void;
  onCreate: (snippet: Snippet) => void;
}

export default function CreateSnippetModal({ token, onClose, onCreate }: Props) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

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
        <form className="overlay-form" onSubmit={handleSubmit}>
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
              <input
                className={`snippet-edit-input snippet-edit-lang${errors.language ? " snippet-edit-input--error" : ""}`}
                placeholder="Language *"
                value={form.language}
                onChange={(e) => {
                  setForm((f) => ({ ...f, language: e.target.value.toUpperCase() }));
                  clearError("language");
                }}
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
            <button
              type="button"
              className="snippet-btn snippet-btn--ghost"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="snippet-btn snippet-btn--primary"
              disabled={saving}
            >
              {saving ? 'Saving…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
