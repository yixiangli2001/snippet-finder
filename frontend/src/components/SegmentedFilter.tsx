interface Option<T extends string> {
  value: T;
  label: string;
}

interface Props<T extends string> {
  label: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}

// A small segmented control (e.g. All / Mine, or All / Public / Private).
// Used to switch which slice of snippets or collections is shown.
export default function SegmentedFilter<T extends string>({ label, value, options, onChange }: Props<T>) {
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map(option => (
        <button
          key={option.value}
          className={`segmented-btn${value === option.value ? ' segmented-btn--active' : ''}`}
          onClick={() => onChange(option.value)}
          aria-pressed={value === option.value}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
