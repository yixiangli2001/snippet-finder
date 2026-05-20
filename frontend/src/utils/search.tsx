/** Escapes special regex characters in a string. */
export function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Wraps every occurrence of `kw` in the text with a highlighted <mark>. */
export function highlight(text: string, kw: string): React.ReactNode {
  if (!kw.trim()) return text;
  const parts = text.split(new RegExp(`(${escapeRegex(kw)})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === kw.toLowerCase()
      ? <mark key={i} className="search-highlight">{part}</mark>
      : part
  );
}

/** Returns up to `maxLines` lines centred around the first line matching `kw`. */
export function getCodeExcerpt(code: string, kw: string, maxLines = 6): string {
  const lines = code.split('\n');
  const matchIdx = kw.trim()
    ? lines.findIndex((l) => l.toLowerCase().includes(kw.toLowerCase()))
    : -1;
  const start = matchIdx === -1 ? 0 : Math.max(0, matchIdx - 1);
  return lines.slice(start, start + maxLines).join('\n');
}
