import { useState, useEffect, useRef } from "react";
import { Upload, Send, FileText, Loader2 } from "lucide-react";
import { listDocuments, uploadDocument, ask } from "./api";
import type { Document, Citation } from "./api";
import "./App.css";

type Message = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

function App() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load documents on mount
  useEffect(() => {
    refreshDocuments();
  }, []);

  // Auto-scroll chat to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
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

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleAsk();
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Office Hours</h1>
        <p>Ask your course material anything.</p>
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
                <div>
                  <div className="doc-name">{doc.name}</div>
                  <div className="doc-meta">{doc.num_pages} pages</div>
                </div>
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
                <p>Ask a question about your indexed course material.</p>
                <p className="hint">
                  Try: "What is the difference between Sunni and Shia Muslims?"
                </p>
              </div>
            )}
            {messages.map((msg, i) => (
              <div key={i} className={`message message-${msg.role}`}>
                <div className="message-content">{msg.content}</div>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="citations">
                    {msg.citations.map((c, j) => (
                      <span key={j} className="citation">
                        {c.doc}, p.{c.page}
                      </span>
                    ))}
                  </div>
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

          {error && <div className="error">{error}</div>}

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