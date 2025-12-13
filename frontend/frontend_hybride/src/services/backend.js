import { API_URL } from "../config";

export async function sendMessage(message, history, session_id) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history, session_id }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Erreur backend");
  }

  return res.json();
}

