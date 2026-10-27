/** API client for the Knowledge Inbox backend. */

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text };
    }
  }

  if (!response.ok) {
    const message =
      (data && (data.detail || data.message)) ||
      `Request failed (${response.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  return data;
}

export function getHealth() {
  return request("/health");
}

export function getItems() {
  return request("/items");
}

export function ingestItem({ type, content }) {
  return request("/ingest", {
    method: "POST",
    body: JSON.stringify({ type, content }),
  });
}

export function queryKnowledge(question) {
  return request("/query", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}
