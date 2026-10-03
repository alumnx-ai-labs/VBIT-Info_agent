import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendChat } from "./api.js";

const SUGGESTIONS = [
  "What courses does VBIT offer and what are their fees?",
  "What documents are required for admission?",
  "Which companies recruit from VBIT?",
  "What facilities does the campus have?",
];

const WELCOME = {
  role: "assistant",
  content: "Hello! I'm the VBIT agent. Ask me about admissions, courses, fees, placements and campus facilities.",
};

const STORE_KEY = "vbit-agent-chats";

const newChat = () => ({ id: crypto.randomUUID(), title: "New chat", messages: [WELCOME] });

// Per-viewer convenience only: the app works fine if storage is unavailable.
function loadChats() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY));
    if (Array.isArray(saved) && saved.length) return saved;
  } catch {}
  return [newChat()];
}

export default function App() {
  const [chats, setChats] = useState(loadChats);
  const [activeId, setActiveId] = useState(() => chats[0].id);
  const [input, setInput] = useState("");
  const [loadingId, setLoadingId] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const endRef = useRef(null);

  const active = chats.find((c) => c.id === activeId) ?? chats[0];
  const loading = loadingId === active.id;
  const messages = active.messages;

  useEffect(() => {
    try { localStorage.setItem(STORE_KEY, JSON.stringify(chats.slice(0, 30))); } catch {}
  }, [chats]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, activeId]);

  const update = (id, fn) => setChats((cs) => cs.map((c) => (c.id === id ? fn(c) : c)));

  function startNewChat() {
    // Reuse an untouched empty chat instead of piling up blank ones.
    const blank = chats.find((c) => c.messages.length === 1);
    if (blank) setActiveId(blank.id);
    else {
      const chat = newChat();
      setChats((cs) => [chat, ...cs]);
      setActiveId(chat.id);
    }
    setInput("");
    setSidebarOpen(false);
  }

  function deleteChat(id) {
    const rest = chats.filter((c) => c.id !== id);
    if (!rest.length) {
      const chat = newChat();
      setChats([chat]);
      setActiveId(chat.id);
    } else {
      setChats(rest);
      if (id === activeId) setActiveId(rest[0].id);
    }
  }

  async function send(text) {
    const question = text.trim();
    if (!question || loadingId) return;
    const id = active.id;
    const next = [...messages, { role: "user", content: question }];
    update(id, (c) => ({
      ...c,
      title: c.title === "New chat" ? question.slice(0, 40) : c.title,
      messages: next,
    }));
    setInput("");
    setLoadingId(id);
    try {
      // The welcome message is UI only; the API history must start with a user turn.
      const { answer, sources, web_sources } = await sendChat(next.slice(1));
      update(id, (c) => ({
        ...c,
        messages: [...next, { role: "assistant", content: answer, sources, webSources: web_sources }],
      }));
    } catch (err) {
      update(id, (c) => ({ ...c, messages: [...next, { role: "assistant", content: err.message, error: true }] }));
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <>
      {/* Faded background image + VBIT watermark share one opacity layer */}
      <div className="bg-layer" aria-hidden="true">
        <div className="bg-image" />
        <div className="bg-title">VBIT</div>
      </div>

      <div className="shell">
        <aside className={sidebarOpen ? "open" : ""}>
          <div className="brand">
            <div className="logo">V</div>
            <strong>VBIT agent</strong>
          </div>
          <button className="new-chat" onClick={startNewChat}>＋ New chat</button>
          <div className="history-label">Recent</div>
          <nav>
            {chats.map((c) => (
              <div key={c.id} className={`history-item${c.id === active.id ? " active" : ""}`}>
                <button onClick={() => { setActiveId(c.id); setSidebarOpen(false); }} title={c.title}>
                  {c.title}
                </button>
                <button className="del" onClick={() => deleteChat(c.id)} aria-label="Delete chat">×</button>
              </div>
            ))}
          </nav>
        </aside>
        {sidebarOpen && <div className="scrim" onClick={() => setSidebarOpen(false)} />}

        <div className="app">
          <header>
            <button className="menu" onClick={() => setSidebarOpen(true)} aria-label="Open menu">☰</button>
            <div className="logo">V</div>
            <div>
              <h1>VBIT agent</h1>
              <p><span className="dot" /> Online · College information assistant</p>
            </div>
          </header>

          <main>
            {messages.map((m, i) => (
              <div key={i} className={`row ${m.role}`}>
                <div className="avatar">{m.role === "user" ? "You" : "V"}</div>
                <div className={`bubble ${m.role}${m.error ? " error" : ""}`}>
                  {m.role === "assistant" && !m.error ? (
                    <div className="md">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                  ) : (
                    <div className="text">{m.content}</div>
                  )}
                  {m.sources?.length > 0 && (
                    <div className="sources">
                      <span>Sources</span>
                      {m.sources.map((s) => (
                        <span key={s} className="chip">{s}</span>
                      ))}
                    </div>
                  )}
                  {m.webSources?.length > 0 && (
                    <div className="sources">
                      <span>Web</span>
                      {m.webSources.map((w) => (
                        <a key={w.url} className="chip" href={w.url} target="_blank" rel="noreferrer">{w.title}</a>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {messages.length === 1 && (
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}

            {loading && (
              <div className="row assistant">
                <div className="avatar">V</div>
                <div className="bubble assistant typing">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={endRef} />
          </main>

          <form onSubmit={(e) => { e.preventDefault(); send(input); }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about VBIT…"
              maxLength={4000}
              autoFocus
            />
            <button type="submit" disabled={!!loadingId || !input.trim()} aria-label="Send">➤</button>
          </form>
        </div>
      </div>
    </>
  );
}
