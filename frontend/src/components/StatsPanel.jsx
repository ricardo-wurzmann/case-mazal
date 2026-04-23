function maxLangCount(languages) {
  if (!languages || typeof languages !== "object") return 0;
  const v = Object.values(languages);
  if (!v.length) return 0;
  return Math.max(...v);
}

function githubUrl(repoFullName) {
  if (!repoFullName) return "#";
  return `https://github.com/${repoFullName.replace(/^\s+|\s+$/g, "")}`;
}

function evidenceBadgeStyle(pct) {
  if (pct > 60) {
    return "bg-emerald-500/20 text-emerald-200 ring-emerald-500/30";
  }
  if (pct > 30) {
    return "bg-amber-500/20 text-amber-200 ring-amber-500/30";
  }
  return "bg-red-500/20 text-red-200 ring-red-500/30";
}

function subproblemBordersAndCounts(reposFound) {
  if (typeof reposFound === "number" && reposFound > 0) {
    return {
      left: "border-l-emerald-500",
      count: "text-emerald-400",
    };
  }
  return {
    left: "border-l-red-500",
    count: "text-red-400",
  };
}

function ExternalLinkIcon() {
  return (
    <svg
      className="mb-0.5 ml-0.5 inline h-3 w-3 text-slate-500"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden
    >
      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
      <path d="M15 3h6v6" />
      <path d="M10 14L21 3" />
    </svg>
  );
}

export default function StatsPanel({ stats, lastIdea, noProjectYet, projectLoading }) {
  if (noProjectYet) {
    return (
      <aside className="flex w-full min-h-[14rem] flex-col items-center justify-center gap-3 rounded-lg border-2 border-slate-800/80 bg-slate-950/80 p-6 text-center shadow-sm shadow-slate-900/20 lg:min-w-0">
        <div
          className="flex h-12 w-12 items-center justify-center rounded-xl border border-sky-500/30 bg-sky-950/50 text-2xl"
          aria-hidden
        >
          🔬
        </div>
        <h2 className="text-sm font-bold uppercase tracking-wide text-slate-200">
          Last project
        </h2>
        <p className="text-balance text-sm leading-relaxed text-slate-500">
          CodeLens decomposes an idea, searches GitHub for how real projects solve each part, and
          streams a reuse plan you can act on. Use the search bar to describe a project to begin.
        </p>
      </aside>
    );
  }

  if (projectLoading) {
    return (
      <aside className="w-full min-w-0 space-y-4 rounded-lg border-2 border-slate-800/80 bg-slate-950/80 p-5">
        <h2 className="text-2xl font-bold tracking-tight text-slate-50">
          <span className="block border-l-4 border-sky-500 pl-2">Last Project</span>
        </h2>
        <p className="flex items-center gap-2 text-sm text-slate-400">
          <span
            className="h-3 w-3 shrink-0 animate-spin rounded-full border-2 border-slate-600 border-t-sky-500"
            aria-hidden
          />
          Gathering code from GitHub…
        </p>
      </aside>
    );
  }

  if (!stats) {
    return (
      <aside className="w-full min-w-0 space-y-3 rounded-lg border-2 border-slate-800/80 bg-slate-950/80 p-5">
        <h2 className="text-2xl font-bold text-slate-100">
          <span className="block border-l-4 border-sky-500 pl-2">Last Project</span>
        </h2>
        {lastIdea && (
          <p className="text-sm text-slate-500">
            No statistics for this run (e.g. error before results).{" "}
            <span className="mt-1 block break-all font-mono text-slate-400" title={lastIdea}>
              Idea: {lastIdea}
            </span>
          </p>
        )}
      </aside>
    );
  }

  const {
    total_repos,
    total_files,
    languages,
    top_repos,
    min_top_score,
    subproblems,
    detected_language,
  } = stats;
  const maxCount = maxLangCount(languages);
  const topFive = (top_repos || []).slice(0, 5);
  const langEntries = Object.entries(languages || {}).sort((a, b) => b[1] - a[1]);
  const spList = Array.isArray(subproblems) ? subproblems : [];
  const n = spList.length;
  const withCode = n ? spList.filter((s) => (s.repos_found || 0) > 0).length : 0;
  const evidencePct = n ? Math.round((withCode / n) * 100) : 0;

  return (
    <aside className="w-full min-w-0 space-y-4 rounded-lg border-2 border-slate-800/80 bg-slate-950/90 p-5">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-slate-50">
          <span className="block border-l-4 border-sky-500 pl-2">Last Project</span>
        </h2>
        {detected_language && (
          <div className="mt-3">
            <span className="inline-block rounded-md bg-sky-500/20 px-3 py-1 text-sm font-semibold text-sky-200 ring-1 ring-sky-500/30">
              Detected: {String(detected_language)}
            </span>
          </div>
        )}
        {lastIdea && (
          <p
            className="mt-2 truncate text-xs font-mono text-slate-400"
            title={lastIdea}
          >
            {lastIdea}
          </p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="rounded-lg border border-slate-800/60 bg-slate-900/70 px-3 py-2">
          <div className="text-[10px] font-medium uppercase text-slate-500">Repositories</div>
          <div className="text-2xl font-bold text-slate-100">{total_repos}</div>
        </div>
        <div className="rounded-lg border border-slate-800/60 bg-slate-900/70 px-3 py-2">
          <div className="text-[10px] font-medium uppercase text-slate-500">Files</div>
          <div className="text-2xl font-bold text-slate-100">{total_files}</div>
        </div>
      </div>

      {n > 0 && (
        <div
          className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium ring-1 ${evidenceBadgeStyle(evidencePct)}`}
        >
          <span>Code evidence</span>
          <span className="font-mono font-bold">
            {evidencePct}%
          </span>
          <span className="text-[10px] font-normal text-slate-500">
            of subproblems with repos
          </span>
        </div>
      )}

      {langEntries.length > 0 && (
        <div>
          <div className="mb-2 text-xs font-semibold text-slate-500">Languages</div>
          <ul className="flex flex-col gap-2.5">
            {langEntries.map(([name, count]) => {
              const pct = maxCount ? (count / maxCount) * 100 : 0;
              return (
                <li key={name} className="text-sm">
                  <div className="mb-0.5 flex items-center justify-between gap-2 text-slate-200">
                    <span className="font-medium leading-tight">{name}</span>
                    <span className="shrink-0 font-mono text-slate-400 tabular-nums">
                      {count}
                    </span>
                  </div>
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-sky-500/90"
                      style={{ width: `${Math.max(4, pct)}%` }}
                    />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {spList.length > 0 && (
        <div className="max-h-[32rem]">
          <div className="mb-2 flex items-end gap-2">
            <h3 className="text-sm font-bold text-slate-200">Subproblem research</h3>
            <span className="h-px flex-1 min-w-8 border-t border-slate-800/60" />
          </div>
          <ul className="flex max-h-72 flex-col gap-2.5 overflow-y-auto pr-1 [scrollbar-width:thin]">
            {spList.map((s, i) => {
              const r = s.repos_found;
              const f = s.files_found;
              const rf = typeof r === "number" && r > 0;
              const { left: leftBorder, count: countCls } = subproblemBordersAndCounts(
                typeof r === "number" ? r : 0
              );
              return (
                <li
                  key={s?.name != null ? `${s.name}-${i}` : i}
                  className={`rounded-lg border border-slate-800/50 border-l-4 ${leftBorder} bg-slate-900/60 p-2.5 pl-2.5 shadow-sm`}
                >
                  <div className="flex items-start justify-between gap-1">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-white">
                        {s.name || "Subproblem"}
                      </div>
                      {s.description && (
                        <p className="mt-0.5 text-xs leading-snug text-slate-400">
                          {s.description}
                        </p>
                      )}
                    </div>
                    <div
                      className={`shrink-0 text-[10px] font-semibold ${countCls} whitespace-nowrap`}
                    >
                      {rf ? (
                        <span>
                          {r} repos · {f ?? 0} files
                        </span>
                      ) : (
                        <span>0 repos · 0 files</span>
                      )}
                    </div>
                  </div>
                  {s.query && (
                    <p className="mt-1.5">
                      <span className="inline-block max-w-full break-all rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[10px] text-slate-200">
                        {s.query}
                      </span>
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {topFive.length > 0 && (
        <div>
          <div className="mb-1.5 text-xs font-semibold text-slate-500">Top repositories</div>
          <ol className="list-outside list-decimal space-y-1.5 pl-4 text-sm">
            {topFive.map((repo) => (
              <li
                key={repo}
                className="pl-0.5 marker:font-mono marker:text-slate-600"
              >
                <a
                  href={githubUrl(repo)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-baseline break-all text-sky-400 hover:underline"
                >
                  {repo}
                  <ExternalLinkIcon />
                </a>
              </li>
            ))}
          </ol>
        </div>
      )}

      <p className="text-[11px] leading-relaxed text-slate-500">
        Top results scored at or above{" "}
        <span className="font-mono text-slate-300">{min_top_score}</span> (higher
        = more relevant by frequency, path, and snippets).
      </p>
    </aside>
  );
}
