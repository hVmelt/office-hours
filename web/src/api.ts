// All HTTP calls to the backend live here.
// Keeping them in one file makes it easy to swap base URLs, add auth, etc.

const API_BASE = "http://localhost:8000";

export type Document = {
  id: number;
  name: string;
  filename: string;
  num_pages: number;
  indexed_at: string;
};

export type Citation = {
  doc: string;
  page: number;
  score: number;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
};

export async function listDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`);
  if (!res.ok) throw new Error(`Failed to list documents: ${res.status}`);
  return res.json();
}

export async function uploadDocument(file: File): Promise<Document> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/documents`, {
    method: "POST",
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, k }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Ask failed: ${res.status}`);
  }
  return res.json();
}