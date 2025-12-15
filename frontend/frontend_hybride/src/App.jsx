import { useState, useEffect, useRef } from "react";
import "./App.css";
import { sendMessage, getPrescription, getSessionLog } from "./services/backend";

// Détection de l'environnement Tauri
const isTauri = () => typeof window !== 'undefined' && window.__TAURI_INTERNALS__ !== undefined;

export default function App() {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Bonjour. Décrivez les symptômes du patient." },
  ]);
  const [sessionId, setSessionId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [dialogueComplete, setDialogueComplete] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [logs, setLogs] = useState(null);
  const [showPrescription, setShowPrescription] = useState(false);
  const [prescription, setPrescription] = useState(null);
  const chatRef = useRef(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

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
      setDialogueComplete(res.dialogue_complete);

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

  async function onPrintPrescription() {
    if (!sessionId) return;
    try {
      const prescriptionText = await getPrescription(sessionId);
      setPrescription(prescriptionText);
      setShowPrescription(true);
    } catch (e) {
      alert("Erreur: " + e.message);
    }
  }

  async function downloadPrescription() {
    try {
      if (isTauri()) {
        // Mode Tauri: utiliser l'API native
        const { save } = await import("@tauri-apps/plugin-dialog");
        const { writeTextFile } = await import("@tauri-apps/plugin-fs");

        const filePath = await save({
          defaultPath: `ordonnance_${sessionId}.txt`,
          filters: [
            { name: "Fichier texte", extensions: ["txt"] },
            { name: "Tous les fichiers", extensions: ["*"] }
          ]
        });

        if (filePath) {
          await writeTextFile(filePath, prescription);
          alert("Ordonnance téléchargée avec succès !");
        }
      } else {
        // Mode navigateur: téléchargement classique
        const blob = new Blob([prescription], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `ordonnance_${sessionId}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      alert("Erreur lors du téléchargement: " + error.message);
    }
  }

  async function onShowLogs() {
    if (!sessionId) return;
    try {
      const logData = await getSessionLog(sessionId);
      setLogs(logData);
      setShowLogs(true);
    } catch (e) {
      alert("Erreur: " + e.message);
    }
  }

  function onRestart() {
    setMessages([
      { role: "assistant", content: "Bonjour. Décrivez les symptômes du patient." },
    ]);
    setSessionId(null);
    setDialogueComplete(false);
    setShowLogs(false);
    setLogs(null);
    setShowPrescription(false);
    setPrescription(null);
  }

  return (
    <div className="page">
      <h1>Assistant médical – Céphalées</h1>

      <div className="chat" ref={chatRef}>
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

      {sessionId && (
        <div className="actions">
          <button onClick={onPrintPrescription}>
            Télécharger ordonnance
          </button>
          <button onClick={onShowLogs}>
            Afficher logs
          </button>
          <button onClick={onRestart} className="restart">
            Nouvelle session
          </button>
        </div>
      )}

      {showLogs && logs && (
        <div className="logs-modal" onClick={() => setShowLogs(false)}>
          <div className="logs-content" onClick={(e) => e.stopPropagation()}>
            <div className="logs-header">
              <h3>Logs de session</h3>
              <button className="close-btn" onClick={() => setShowLogs(false)}>X</button>
            </div>
            <pre>{JSON.stringify(logs, null, 2)}</pre>
            <button onClick={() => setShowLogs(false)}>Fermer</button>
          </div>
        </div>
      )}

      {showPrescription && prescription && (
        <div className="logs-modal" onClick={() => setShowPrescription(false)}>
          <div className="logs-content prescription-content" onClick={(e) => e.stopPropagation()}>
            <div className="logs-header">
              <h3>Ordonnance</h3>
              <button className="close-btn" onClick={() => setShowPrescription(false)}>X</button>
            </div>
            <pre>{prescription}</pre>
            <div className="prescription-actions">
              <button onClick={downloadPrescription}>Télécharger</button>
              <button onClick={() => setShowPrescription(false)}>Fermer</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
