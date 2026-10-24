import { useMemo, useRef, useState } from "react";
import type { SearchEntry } from "../lib/search";
import { rankText, searchTaxa } from "../lib/search";

interface Props {
  index: SearchEntry[];
  onJump: (id: number) => void;
}

export function SearchBox({ index, onJump }: Props) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const results = useMemo(() => searchTaxa(index, query), [index, query]);

  function choose(entry: SearchEntry) {
    onJump(entry.id);
    setQuery("");
    setOpen(false);
    inputRef.current?.blur();
  }

  return (
    <div
      className="search"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setOpen(false);
        }
      }}
    >
      <div className="search-input-wrap">
        <span className="search-icon" aria-hidden="true">
          ⌕
        </span>
        <input
          ref={inputRef}
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setQuery("");
              setOpen(false);
              inputRef.current?.blur();
            }
            if (event.key === "Enter" && results[0]) {
              choose(results[0]);
            }
          }}
          placeholder="搜中文名、拉丁名或拼音…"
          aria-label="搜索分类阶元"
          autoComplete="off"
        />
        {query && (
          <button
            className="search-clear"
            type="button"
            onClick={() => {
              setQuery("");
              inputRef.current?.focus();
            }}
            aria-label="清空搜索"
          >
            ×
          </button>
        )}
      </div>

      {open && query.trim() && (
        <div className="search-results" role="listbox">
          {results.length === 0 ? (
            <div className="search-empty">没有匹配的阶元，试试上级分类。</div>
          ) : (
            results.map((entry) => (
              <button
                key={entry.id}
                type="button"
                className="search-result"
                role="option"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(entry)}
              >
                <span className={`rank-pill rank-${entry.rank}`}>
                  {rankText(entry.rank)}
                </span>
                <span className="search-result-main">
                  <span className="search-result-name">
                    {entry.zh ?? entry.name}
                    {entry.zh && <em>{entry.name}</em>}
                  </span>
                  <span className="search-result-path">{entry.path}</span>
                </span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
