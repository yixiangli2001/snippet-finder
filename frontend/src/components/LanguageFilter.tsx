import './LanguageFilter.css';

interface Props {
  languages: string[];
  value: string;
  onChange: (language: string) => void;
}

export default function LanguageFilter({ languages, value, onChange }: Props) {
  if (languages.length === 0) return null;

  return (
    <div className="lang-filter" role="group" aria-label="Filter by language">
      <button
        className={`lang-chip${value === '' ? ' lang-chip--active' : ''}`}
        onClick={() => onChange('')}
      >
        All
      </button>
      {languages.map(lang => (
        <button
          key={lang}
          className={`lang-chip${value === lang ? ' lang-chip--active' : ''}`}
          onClick={() => onChange(lang === value ? '' : lang)}
          aria-pressed={value === lang}
        >
          {lang.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
