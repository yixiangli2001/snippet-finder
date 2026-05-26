interface Props {
  languages: string[];
  value: string;
  onChange: (language: string) => void;
}

export default function LanguageFilter({ languages, value, onChange }: Props) {
  if (languages.length === 0) return null;

  return (
    <div className="filter-bar">
      <select
        className="filter-dropdown"
        value={value}
        onChange={e => onChange(e.target.value)}
        aria-label="Filter by language"
      >
        <option value="">All languages</option>
        {languages.map(lang => (
          <option key={lang} value={lang}>
            {lang.toUpperCase()}
          </option>
        ))}
      </select>
    </div>
  );
}
