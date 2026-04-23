import { isValidElement, useEffect, useRef, useState, cloneElement } from "react";
import ReactMarkdown from "react-markdown";

function textFromNode(ch) {
  if (ch == null) return "";
  if (typeof ch === "string" || typeof ch === "number") return String(ch);
  if (Array.isArray(ch)) return ch.map(textFromNode).join("");
  if (isValidElement(ch) && ch.props) return textFromNode(ch.props.children);
  return "";
}

function PreWithCopy({ children }) {
  const [copied, setCopied] = useState(false);
  if (!isValidElement(children) || !children.props) {
    return (
      <pre className="my-3 max-w-full overflow-x-auto rounded-lg border border-slate-700/60 bg-slate-800 p-3 text-sm text-slate-200">
        {children}
      </pre>
    );
  }

  const className = String(children.props.className || "");
  const m = /language-(\w+)/.exec(className);
  const lang = m ? m[1] : "code";
  const raw = textFromNode(children.props.children);

  const onCopy = () => {
    if (raw) {
      void navigator.clipboard.writeText(raw);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      data-codelens-code
      className="group relative my-3 w-full min-w-0 max-w-none overflow-hidden rounded-lg border border-slate-600/50 bg-slate-800"
    >
      <div className="absolute right-0 top-0 z-20 flex max-w-[calc(100%-0.5rem)] items-center gap-1.5 p-2 pl-0">
        <span className="shrink-0 font-mono text-[10px] font-semibold uppercase leading-none tracking-wider text-slate-300/95">
          {lang}
        </span>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex h-6 w-6 flex-shrink-0 items-center justify-center rounded border border-slate-500/50 bg-slate-900/95 text-slate-400 opacity-0 shadow-sm transition group-hover:opacity-100 focus:opacity-100 hover:border-slate-400 hover:text-slate-100"
          title="Copy"
          aria-label="Copy code"
        >
          {copied ? (
            <span className="text-xs text-emerald-400" aria-hidden>
              ✓
            </span>
          ) : (
            <svg
              className="h-3.5 w-3.5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden
            >
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
      </div>
      <pre className="!m-0 !mt-0 !mb-0 !bg-transparent p-0 pt-8 [scrollbar-width:thin] [scrollbar-color:theme(colors.slate.500)_theme(colors.slate.900)]">
        {cloneElement(children, {
          className: `${className} block w-full min-w-0 max-w-full overflow-x-auto p-3 font-mono text-sm !leading-relaxed !text-slate-100 [tab-size:2]`,
        })}
      </pre>
    </div>
  );
}

function CodeRenderer({ className, children, ...rest }) {
  if (String(className || "").includes("language-")) {
    return (
      <code className={className} {...rest}>
        {children}
      </code>
    );
  }
  return (
    <code
      className="rounded border border-slate-600/40 bg-slate-800/80 px-1.5 py-0.5 font-mono text-[0.9em] text-sky-200/95"
      {...rest}
    >
      {children}
    </code>
  );
}

const CHAT_MARKDOWN = {
  pre: PreWithCopy,
  code: CodeRenderer,
};

function DecompositionCard({ subproblems }) {
  const n = (subproblems && subproblems.length) || 0;
  if (!n) return null;
  return (
    <div className="max-w-full rounded-2xl rounded-tl-md border border-indigo-500/30 border-l-4 border-l-indigo-500/70 bg-indigo-950/40 px-4 py-3 text-sm text-slate-200 shadow-sm ring-1 ring-indigo-400/10">
      <h3 className="mb-2 text-sm font-semibold text-indigo-100/95">
        🔍 Researching {n} {n === 1 ? "subproblem" : "subproblems"}
      </h3>
      <ul className="flex flex-col gap-2.5">
        {(subproblems || []).map((s, i) => (
          <li
            key={s?.name != null ? `${s.name}-${i}` : i}
            className="border-l-2 border-indigo-500/50 pl-3"
          >
            <div className="font-semibold text-slate-100">
              {s.name || "Subproblem"}
            </div>
            {s.description ? (
              <p className="mt-0.5 text-xs text-slate-400">{s.description}</p>
            ) : null}
            {s.query ? (
              <p className="mt-1.5">
                <span className="inline-block max-w-full break-all rounded border border-slate-600/50 bg-slate-900/60 px-1.5 py-0.5 font-mono text-[10px] leading-snug text-slate-300">
                  {s.query}
                </span>
              </p>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ChatWindow({ messages, isStreaming, emptyHint }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming, messages.length]);

  return (
    <section className="flex h-full min-h-0 flex-col rounded-lg border border-slate-800/80 bg-slate-950/40">
      <div className="shrink-0 border-b border-slate-800/60 px-4 py-2 text-xs font-medium uppercase tracking-wider text-slate-500">
        Conversation
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-4 [scrollbar-width:thin] [scrollbar-color:theme(colors.slate.600)_theme(colors.slate.900)]">
        {messages.length === 0 && !isStreaming && (
          <p className="text-center text-sm text-slate-500">{emptyHint}</p>
        )}
        <ul className="flex w-full min-w-0 flex-col gap-4">
          {messages.map((m) => {
            if (m.role === "decomposition") {
              return (
                <li key={m.id} className="w-full min-w-0 max-w-full">
                  <DecompositionCard subproblems={m.subproblems} />
                </li>
              );
            }
            if (m.role === "user") {
              return (
                <li
                  key={m.id}
                  className="ml-auto w-full min-w-0 max-w-[92%] rounded-2xl rounded-tr-md bg-slate-800/90 px-4 py-2.5 text-sm text-slate-100"
                >
                  <p className="whitespace-pre-wrap break-words">{m.content}</p>
                </li>
              );
            }
            if (m.role === "assistant") {
              return (
                <li
                  key={m.id}
                  className="w-full min-w-0 max-w-full rounded-2xl rounded-tl-md border border-slate-800/80 bg-slate-900/50 px-3 py-2.5 sm:px-4"
                >
                  <div className="codelens-md min-w-0 max-w-none text-sm text-slate-200">
                    {m.content ? (
                      <ReactMarkdown components={CHAT_MARKDOWN}>
                        {m.content}
                      </ReactMarkdown>
                    ) : isStreaming ? (
                      <span className="text-slate-500">…</span>
                    ) : null}
                  </div>
                </li>
              );
            }
            return null;
          })}
        </ul>
        {isStreaming && (
          <div className="mt-2 flex items-center gap-2 text-sm text-slate-500">
            <span
              className="inline-block h-2 w-2 animate-pulse rounded-full bg-sky-500"
              aria-hidden
            />
            <span>Assistant is writing…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
