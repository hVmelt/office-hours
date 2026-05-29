// All HTTP calls to the backend live here.
// Keeping them in one file makes it easy to swap base URLs, add auth, etc.

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

// A stable per-browser session ID, generated once and persisted.
// This is how the backend isolates each visitor's uploaded documents.
function getSessionId(): string {
  let id = localStorage.getItem("office-hours-session");
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem("office-hours-session", id);
  }
  return id;
}

export type Document = {
  id: number;
  name: string;
  filename: string;
  num_pages: number;
  indexed_at: string;
  is_demo: boolean;
};

export type Citation = {
  doc: string;
  page: number;
  score: number;
  text: string;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
};

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    headers: { "X-Session-Id": getSessionId() },
  });
  if (!res.ok) throw new Error(`Failed to list documents: ${res.status}`);
  return res.json();
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
    headers: { "X-Session-Id": getSessionId() },
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}

export async function ask(question: string, k = 5): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Session-Id": getSessionId(),
    },
    body: JSON.stringify({ question, k }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Ask failed: ${res.status}`);
  }
  return res.json();
}

export async function deleteDocument(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: "DELETE",
    headers: { "X-Session-Id": getSessionId() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Delete failed: ${res.status}`);
  }
}