import { useState } from 'react';
import { LANGUAGES } from '../constants';

interface Props {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  onClearError?: () => void;
}

export function LanguageSelect({ value, onChange, error, onClearError }: Props) {
  // Start in "Other" mode if the current value isn't in the standard list.
  const [isOther, setIsOther] = useState(
    () => value !== '' && !LANGUAGES.includes(value as typeof LANGUAGES[number])
  );

  const errorClass = error ? ' snippet-edit-input--error' : '';

  function handleSelectChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onClearError?.();
    if (e.target.value === 'OTHER') {
      setIsOther(true);
      onChange('');
    } else {
      setIsOther(false);
      onChange(e.target.value);
    }
  }

  function handleBackToList() {
    setIsOther(false);
    onChange('');
    onClearError?.();
  }

  if (isOther) {
    // Replace the dropdown with a text input when "Other" is selected, and add a back button to return to the dropdown.
    return (
      <div className="language-select-wrap">
        <div className="language-other-row">
          <input
            className={`snippet-edit-input snippet-edit-lang${errorClass}`}
            placeholder="e.g. BASH"
            value={value}
            onChange={e => { onChange(e.target.value.toUpperCase()); onClearError?.(); }}
            autoFocus
          />
          <button
            type="button"
            className="language-back-btn"
            onClick={handleBackToList}
            title="Choose from list"
          >
            ↩
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="language-select-wrap">
      <select
        className={`snippet-edit-input snippet-edit-lang snippet-edit-select${errorClass}`}
        value={value || ''}
        onChange={handleSelectChange}
      >
        <option value="" disabled>Language *</option>
        {LANGUAGES.map(lang => (
          <option key={lang} value={lang}>{lang}</option>
        ))}
        <option value="OTHER">Other…</option>
      </select>
    </div>
  );
}
