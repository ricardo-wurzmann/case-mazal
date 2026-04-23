import { useCallback, useState } from "react";
import { streamProject } from "./lib/api";
import SearchBar from "./components/SearchBar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import StatsPanel from "./components/StatsPanel.jsx";

let msgId = 0;
const newId = () => {
  msgId += 1;
  return `m-${msgId}`;
};

const EMPTY_HINT =
  "Describe a project to research: we break it into subproblems, scan GitHub, then stream an architecture and reuse plan here.";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [currentStats, setCurrentStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastIdea, setLastIdea] = useState("");
  const [statusText, setStatusText] = useState("");

  const handleSearch = useCallback(async (idea) => {
    setLastIdea(idea);
    setIsLoading(true);
    setStatusText("");
    setCurrentStats(null);

    const userMsg = { id: newId(), role: "user", content: idea };
    const asstId = newId();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: asstId, role: "assistant", content: "" },
    ]);

    let gotDone = false;
    const finish = () => {
      if (gotDone) return;
      gotDone = true;
      setIsLoading(false);
      setStatusText("");
    };

    const insertDecomposition = (data) => {
      const subproblems = Array.isArray(data) ? data : [];
      if (!subproblems.length) return;
      const dId = newId();
      setMessages((prev) => {
        const i = prev.findIndex((m) => m.id === asstId);
        if (i < 0) {
          return [
            ...prev,
            {
              id: dId,
              role: "decomposition",
              subproblems,
            },
          ];
        }
        return [
          ...prev.slice(0, i),
          { id: dId, role: "decomposition", subproblems },
          ...prev.slice(i),
        ];
      });
    };

    await streamProject(idea, {
      onStatus: (msg) => setStatusText(msg),
      onDecomposition: (d) => insertDecomposition(d),
      onStats: (s) => setCurrentStats(s),
      onToken: (t) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstId ? { ...m, content: m.content + t } : m
          )
        );
      },
      onDone: () => {
        finish();
      },
      onError: (err) => {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === asstId
              ? {
                  ...m,
                  content: m.content
                    ? `${m.content}\n\n*${err}*`
                    : `*${err}*`,
                }
              : m
            )
        );
        setStatusText("");
      },
      onHttpError: (status) => {
        if (status === 429) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstId
                ? { ...m, content: `*GitHub rate limit — try again in a few minutes.*` }
                : m
            )
          );
        } else {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstId
                ? { ...m, content: `*Request failed (${status}).*` }
                : m
            )
          );
        }
        setStatusText("");
        if (!gotDone) {
          gotDone = true;
          setIsLoading(false);
        }
      },
    });
  }, []);

  return (
    <div
      style={{ height: "100dvh" }}
      className="flex flex-col overflow-hidden bg-slate-900 text-slate-100"
    >
      <div className="shrink-0 border-b border-slate-800/50 px-4 py-3 text-center sm:text-left">
        <h1 className="text-base font-semibold tracking-tight text-slate-100 sm:text-lg">
          CodeLens
        </h1>
        <p className="text-xs text-slate-500 sm:text-sm">
          Deep research in GitHub code — with streaming analysis
        </p>
      </div>

      <SearchBar
        onSubmit={handleSearch}
        isLoading={isLoading}
        disabled={isLoading}
        statusMessage={statusText}
      />

      <div className="mx-auto flex min-h-0 w-full max-w-7xl flex-1 flex-col gap-3 overflow-hidden px-4 pb-4 pt-2 lg:flex-row">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <ChatWindow
            messages={messages}
            isStreaming={isLoading}
            emptyHint={EMPTY_HINT}
          />
        </div>
        <div className="min-h-0 shrink-0 overflow-y-auto lg:w-96">
          <StatsPanel
            stats={currentStats}
            lastIdea={lastIdea}
            noProjectYet={!lastIdea}
            projectLoading={isLoading && !!lastIdea && !currentStats}
          />
        </div>
      </div>
    </div>
  );
}
