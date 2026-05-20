import { type Snippet } from './CodeSnippet';
import { highlight, getCodeExcerpt } from '../utils/search';

interface Props {
  query: string;
  setQuery: (q: string) => void;
  results: Snippet[];
  isOpen: boolean;
  selectedIdx: number;
  setSelectedIdx: (i: number) => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  copyResult: (s: Snippet) => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLInputElement>) => void;
  onFocus: () => void;
  onBlur: () => void;
  cancelClose: () => void;
}

export default function SearchBar({
  query, setQuery,
  results, isOpen,
  selectedIdx, setSelectedIdx,
  inputRef,
  copyResult, onKeyDown, onFocus, onBlur, cancelClose,
}: Props) {
  return (
    <div className="search-wrap" onMouseDown={cancelClose}>
      <input
        ref={inputRef}
        className="search-input"
        placeholder="Search snippets…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={onFocus}
        onBlur={onBlur}
        autoComplete="off"
        spellCheck={false}
      />

      {isOpen && results.length > 0 && (
        <ul className="search-dropdown" role="listbox">
          {results.map((s, i) => (
            <li
              key={s.id}
              role="option"
              aria-selected={i === selectedIdx}
              className={`search-result${i === selectedIdx ? ' search-result--active' : ''}`}
              onMouseEnter={() => setSelectedIdx(i)}
              onMouseDown={(e) => { e.preventDefault(); copyResult(s); }}
            >
              <div className="search-result-header">
                <span className="search-result-lang">{s.language}</span>
                <span className="search-result-title">{highlight(s.title, query)}</span>
                {s.tags.length > 0 && (
                  <span className="search-result-tags">
                    {s.tags.slice(0, 3).map((t) => (
                      <span key={t} className="search-result-tag">{highlight(t, query)}</span>
                    ))}
                  </span>
                )}
                <span className="search-result-hint">↵ copy</span>
              </div>

              {s.description && (
                <p className="search-result-desc">{highlight(s.description, query)}</p>
              )}

              <pre className="search-result-code">
                <code>{highlight(getCodeExcerpt(s.code, query), query)}</code>
              </pre>
            </li>
          ))}
        </ul>
      )}

      {isOpen && results.length === 0 && query.trim() && (
        <div className="search-empty">No snippets found</div>
      )}
    </div>
  );
}
