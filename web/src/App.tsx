import { useState, useEffect, useRef } from "react";
import { Upload, Send, FileText, Loader2, Trash2, Sun, Moon } from "lucide-react";
import { listDocuments, uploadDocument, ask, deleteDocument } from "./api";
import type { Document, Citation } from "./api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import "./App.css";

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

function CitationList({ citations }: { citations: Citation[] }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div className="citations">
      <div className="citation-chips">
        {citations.map((c, j) => (
          <button
            key={j}
            className={`citation ${expanded === j ? "active" : ""}`}
            onClick={() => setExpanded(expanded === j ? null : j)}
          >
            {c.doc}, p.{c.page}
          </button>
        ))}
      </div>
      {expanded !== null && (
        <div className="citation-preview">
          <div className="citation-preview-header">
            {citations[expanded].doc} — page {citations[expanded].page}
          </div>
          <div className="citation-preview-text">
            {citations[expanded].text}
          </div>
        </div>
      )}
    </div>
  );
}

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = localStorage.getItem("office-hours-chat");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [theme, setTheme] = useState<"light" | "dark">(() => {
  const saved = localStorage.getItem("office-hours-theme");
  if (saved === "dark" || saved === "light") return saved;
  // Default to user's OS preference
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
});

useEffect(() => {
  document.documentElement.setAttribute("data-theme", theme);
  localStorage.setItem("office-hours-theme", theme);
}, [theme]);

  // Load documents on mount
  useEffect(() => {
    refreshDocuments();
  }, []);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Persist chat across page refreshes
useEffect(() => {
  localStorage.setItem("office-hours-chat", JSON.stringify(messages));
}, [messages]);

  async function refreshDocuments() {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      await uploadDocument(file);
      await refreshDocuments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
      e.target.value = ""; // reset so user can re-upload same file
    }
  }

  async function handleAsk() {
    const question = input.trim();
    if (!question || loading) return;

    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", content: question }]);
    setLoading(true);

    try {
      const response = await ask(question);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: response.answer,
          citations: response.citations,
        },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to get answer");
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!confirm(`Delete "${name}" and all its chunks?`)) return;
    try {
      await deleteDocument(id);
      await refreshDocuments();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Office Hours</h1>
          <p>Ask your course material anything.</p>
        </div>
        <div className="header-actions">
          {messages.length > 0 && (
            <button className="clear-btn" onClick={() => setMessages([])}>
              Clear chat
            </button>
          )}
          <button
            className="theme-btn"
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? <Moon size={16} /> : <Sun size={16} />}
          </button>
        </div>
      </header>

      <div className="layout">
        <aside className="sidebar">
          <h2>Documents</h2>
          <ul className="doc-list">
            {documents.length === 0 && (
              <li className="empty">No documents indexed yet.</li>
            )}
            {documents.map((doc) => (
              <li key={doc.id} className="doc-item">
                <FileText size={16} />
                <div className="doc-info">
                  <div className="doc-name">{doc.name}</div>
                  <div className="doc-meta">
                    {doc.num_pages} pages{doc.is_demo ? " · demo" : ""}
                  </div>
                </div>
                {!doc.is_demo && (
                  <button
                    className="doc-delete"
                    onClick={() => handleDelete(doc.id, doc.name)}
                    title="Delete document"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>

          <label className="upload-btn">
            {uploading ? (
              <>
                <Loader2 size={16} className="spin" />
                Indexing...
              </>
            ) : (
              <>
                <Upload size={16} />
                Upload PDF
              </>
            )}
            <input
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={uploading}
              hidden
            />
          </label>
        </aside>

        <main className="chat">
          <div className="messages">
            {messages.length === 0 && (
              <div className="welcome">
                <p>Ask a question about your indexed course material or something totally unrelated.</p>
                <p className="hint">
                  Try: "Who is Batman"
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message message-${msg.role}`}>
                <div className="message-content">
                  {msg.role === "assistant" ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content}
                  </ReactMarkdown>) : (msg.content)}
                </div>
                {msg.citations && msg.citations.length > 0 && (
                  <CitationList citations={msg.citations} />
                )}
              </div>
            ))}
            {loading && (
              <div className="message message-assistant">
                <div className="message-content loading-msg">
                  <Loader2 size={16} className="spin" />
                  Thinking...
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <div className="error">
              <div className="error-content">
                <span className="error-label">Error:</span> {error}
              </div>
              <button className="error-dismiss" onClick={() => setError(null)}>
                ×
              </button>
            </div>
          )}

          <div className="input-row">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question..."
              rows={2}
              disabled={loading}
            />
            <button onClick={handleAsk} disabled={loading || !input.trim()}>
              <Send size={18} />
            </button>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;