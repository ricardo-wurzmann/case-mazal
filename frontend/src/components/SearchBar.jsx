export default function SearchBar({ onSubmit, isLoading, disabled, statusMessage }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    const form = e.currentTarget;
    const fd = new FormData(form);
    const q = (fd.get("q") || "").toString().trim();
    if (!q || isLoading) return;
    onSubmit(q);
  };

  return (
    <header className="shrink-0 border-b border-slate-800/80 bg-slate-950/60 backdrop-blur">
      <form
        onSubmit={handleSubmit}
        className="mx-auto flex w-full max-w-5xl flex-col gap-0 px-4 py-4"
      >
        <div className="flex w-full items-end gap-3">
          <label className="min-w-0 flex-1 text-sm text-slate-500">
            <span className="mb-1 block text-xs font-medium uppercase tracking-wider text-slate-500">
              Query
            </span>
            <input
              name="q"
              type="search"
              autoComplete="off"
              disabled={disabled || isLoading}
              placeholder="Describe your project idea... (e.g. 'video transcriber in Python', 'REST API with JWT auth')"
              className="w-full rounded-lg border border-slate-700/90 bg-slate-900/80 px-3 py-2.5 text-slate-100 placeholder-slate-500 ring-sky-500/40 focus:border-sky-500/60 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60"
            />
          </label>
          <button
            type="submit"
            disabled={disabled || isLoading}
            className="inline-flex h-[42px] min-w-[100px] shrink-0 items-center justify-center gap-2 rounded-lg bg-sky-600 px-4 text-sm font-medium text-white shadow transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <span
                  className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-white/30 border-t-white"
                  aria-hidden
                />
                <span>Researching</span>
              </>
            ) : (
              "Research"
            )}
          </button>
        </div>
        {statusMessage && (
          <div
            className="flex items-center gap-2 px-1 py-1 text-xs text-sky-400"
            aria-live="polite"
          >
            <span
              className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-sky-400"
              aria-hidden
            />
            {statusMessage}
          </div>
        )}
      </form>
    </header>
  );
}
