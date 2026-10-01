// Empty in dev/single-service mode (same-origin /api). On Vercel, set VITE_API_URL
// to the Render backend URL, e.g. https://vbit-agent.onrender.com
const API_URL = (import.meta.env.VITE_API_URL || "").replace(/\/+$/, "");

export async function sendChat(messages) {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages.map(({ role, content }) => ({ role, content })),
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${res.status})`);
  }
  return res.json();
}
