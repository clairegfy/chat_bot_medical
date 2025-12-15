// src/App.jsx
import { useState } from "react";
import "./index.css";
import { analyserTexte, getPrescription, resetConversation, getSessionLog } from "./services/analyseService";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [dialogueComplete, setDialogueComplete] = useState(false);
  const [modal, setModal] = useState({ open: false, title: "", content: "", type: "" });

  const sendMessage = async () => {
    if (!input.trim()) return;

    // message utilisateur
    setMessages((prev) => [...prev, { role: "user", text: input }]);

    try {
      const data = await analyserTexte(input);

      // Afficher directement le message du bot (dialogue conversationnel)
      setMessages((prev) => [...prev, { role: "bot", text: data.decision }]);

      // Vérifier si le dialogue est terminé
      if (data.dialogueComplete) {
        setDialogueComplete(true);
      }
    } catch (error) {
      console.error(error);
      setMessages((prev) => [
        ...prev,
        {
          role: "bot",
          text: "Erreur : impossible de joindre le backend arbre.",
        },
      ]);
    }

    setInput("");
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter") sendMessage();
  };

  const handlePrintPrescription = async () => {
    const doctorName = prompt("Nom du médecin prescripteur:", "Dr. ");
    if (!doctorName) return;

    try {
      const prescriptionText = await getPrescription(doctorName);
      setModal({
        open: true,
        title: "Ordonnance",
        content: prescriptionText,
        type: "prescription"
      });
    } catch (error) {
      console.error(error);
      alert("Erreur lors de la génération de l'ordonnance: " + error.message);
    }
  };

  const handleNewConsultation = () => {
    resetConversation();
    setMessages([]);
    setDialogueComplete(false);
  };

  const handleShowLog = async () => {
    try {
      const logData = await getSessionLog();
      setModal({
        open: true,
        title: "Log de session",
        content: logData,
        type: "log"
      });
    } catch (error) {
      console.error(error);
      alert("Erreur lors de la récupération du log: " + error.message);
    }
  };

  const closeModal = () => {
    setModal({ open: false, title: "", content: "", type: "" });
  };

  const handlePrint = () => {
    window.print();
  };

  const renderLogContent = (log) => {
    return (
      <div style={{ textAlign: "left" }}>
        <p><strong>Session ID:</strong> {log.session_id}</p>
        <p><strong>Messages échangés:</strong> {log.message_count}</p>

        {log.analysis && (
          <>
            <h4 style={{ marginTop: "15px", borderBottom: "1px solid #ddd", paddingBottom: "5px" }}>Analyse</h4>
            <p><strong>Red flags:</strong> <span style={{ color: log.analysis.has_red_flags ? "#dc3545" : "#28a745" }}>{log.analysis.has_red_flags ? "Oui" : "Non"}</span></p>
            <p><strong>Urgence:</strong> <span style={{ color: log.analysis.is_emergency ? "#dc3545" : "#28a745" }}>{log.analysis.is_emergency ? "Oui" : "Non"}</span></p>
            <p><strong>Profil:</strong> {log.analysis.profile}</p>
            <p><strong>Onset:</strong> {log.analysis.onset}</p>
          </>
        )}

        {log.asked_fields && log.asked_fields.length > 0 && (
          <>
            <h4 style={{ marginTop: "15px", borderBottom: "1px solid #ddd", paddingBottom: "5px" }}>Champs demandés</h4>
            <ul>
              {log.asked_fields.map((f, i) => <li key={i}>{f}</li>)}
            </ul>
          </>
        )}

        {log.extraction_metadata && Object.keys(log.extraction_metadata).length > 0 && (
          <>
            <h4 style={{ marginTop: "15px", borderBottom: "1px solid #ddd", paddingBottom: "5px" }}>Métadonnées NLU</h4>
            <pre style={{ background: "#f5f5f5", padding: "10px", borderRadius: "4px", overflow: "auto", fontSize: "12px" }}>
              {JSON.stringify(log.extraction_metadata, null, 2)}
            </pre>
          </>
        )}

        {log.case_data && (
          <>
            <h4 style={{ marginTop: "15px", borderBottom: "1px solid #ddd", paddingBottom: "5px" }}>Données du cas</h4>
            <pre style={{ background: "#f5f5f5", padding: "10px", borderRadius: "4px", overflow: "auto", fontSize: "12px" }}>
              {JSON.stringify(log.case_data, null, 2)}
            </pre>
          </>
        )}
      </div>
    );
  };

  return (
    <div
      style={{
        fontFamily: "Arial, sans-serif",
        padding: "20px",
        maxWidth: "600px",
        margin: "0 auto",
      }}
    >
      <h2 style={{ textAlign: "center", marginBottom: "10px" }}>
        Assistant – arbre décisionnel
      </h2>
      <p style={{ textAlign: "center", color: "#666", marginBottom: "20px" }}>
        Saisissez un cas clinique pour obtenir une recommandation d'imagerie.
      </p>

      {/* zone messages */}
      <div
        style={{
          border: "1px solid #ddd",
          borderRadius: "8px",
          padding: "10px",
          minHeight: "180px",
          marginBottom: "10px",
        }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              margin: "5px 0",
            }}
          >
            <div
              style={{
                background: m.role === "user" ? "#d1e7ff" : "#f3f3f3",
                padding: "8px 12px",
                borderRadius: "15px",
                maxWidth: "80%",
                whiteSpace: "pre-wrap",
              }}
            >
              {m.text}
            </div>
          </div>
        ))}
      </div>

      {/* input */}
      <div style={{ display: "flex", gap: "8px", marginTop: "10px" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyPress}
          placeholder="Décrivez le cas clinique..."
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: "12px",
            border: "1px solid #ccc",
          }}
        />
        <button
          onClick={sendMessage}
          style={{
            padding: "8px 16px",
            borderRadius: "12px",
            border: "none",
            background: "#2f6fed",
            color: "white",
            cursor: "pointer",
          }}
        >
          Envoyer
        </button>
      </div>

      {/* Boutons d'action quand dialogue terminé */}
      {dialogueComplete && (
        <div style={{ display: "flex", gap: "8px", marginTop: "15px", justifyContent: "center", flexWrap: "wrap" }}>
          <button
            onClick={handlePrintPrescription}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              border: "none",
              background: "#28a745",
              color: "white",
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            Ordonnance
          </button>
          <button
            onClick={handleShowLog}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              border: "none",
              background: "#6c757d",
              color: "white",
              cursor: "pointer",
            }}
          >
            Afficher log
          </button>
          <button
            onClick={handleNewConsultation}
            style={{
              padding: "10px 20px",
              borderRadius: "12px",
              border: "1px solid #ccc",
              background: "white",
              color: "#333",
              cursor: "pointer",
            }}
          >
            Nouvelle consultation
          </button>
        </div>
      )}

      {/* Modal */}
      {modal.open && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
          }}
          onClick={closeModal}
        >
          <div
            style={{
              background: "white",
              borderRadius: "12px",
              padding: "20px",
              maxWidth: "90%",
              maxHeight: "80%",
              overflow: "auto",
              minWidth: "300px",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
              <h3 style={{ margin: 0 }}>{modal.title}</h3>
              <button
                onClick={closeModal}
                style={{
                  background: "none",
                  border: "none",
                  fontSize: "24px",
                  cursor: "pointer",
                  color: "#666",
                }}
              >
                ×
              </button>
            </div>

            {modal.type === "prescription" ? (
              <pre style={{
                whiteSpace: "pre-wrap",
                fontFamily: "monospace",
                fontSize: "12px",
                background: "#f9f9f9",
                padding: "15px",
                borderRadius: "8px",
              }}>
                {modal.content}
              </pre>
            ) : (
              renderLogContent(modal.content)
            )}

            <div style={{ marginTop: "15px", display: "flex", gap: "10px", justifyContent: "flex-end" }}>
              {modal.type === "prescription" && (
                <button
                  onClick={handlePrint}
                  style={{
                    padding: "8px 16px",
                    borderRadius: "8px",
                    border: "none",
                    background: "#28a745",
                    color: "white",
                    cursor: "pointer",
                  }}
                >
                  Imprimer
                </button>
              )}
              <button
                onClick={closeModal}
                style={{
                  padding: "8px 16px",
                  borderRadius: "8px",
                  border: "1px solid #ccc",
                  background: "white",
                  cursor: "pointer",
                }}
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
