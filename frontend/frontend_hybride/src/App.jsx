import { useState } from "react";
import "./App.css";
import { sendMessage } from "./services/backend";

export default function App() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Bonjour. Décrivez les symptômes du patient." },
  ]);
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSend() {
    if (!input.trim() || loading) return;

    const userMsg = { role: "user", content: input };
    const newHistory = [...messages, userMsg];

    setMessages(newHistory);
    setInput("");
    setLoading(true);

    try {
      const res = await sendMessage(input, newHistory, sessionId);
      setSessionId(res.session_id);

      setMessages([
        ...newHistory,
        { role: "assistant", content: res.message },
      ]);
    } catch (e) {
      setMessages([
        ...newHistory,
        { role: "assistant", content: "Erreur: impossible de joindre le backend." },
      ]);
      console.error(e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page">
      <h1>Assistant médical – Céphalées</h1>

      <div className="chat">
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="bubble">{m.content}</div>
          </div>
        ))}
        {loading && (
          <div className="msg assistant">
            <div className="bubble">…</div>
          </div>
        )}
      </div>

      <div className="composer">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Tapez votre message…"
          onKeyDown={(e) => e.key === "Enter" && onSend()}
        />
        <button onClick={onSend} disabled={loading}>
          Envoyer
        </button>
      </div>

      <div className="meta">
        <small>Session: {sessionId ?? "—"}</small>
      </div>
    </div>
  );
}
