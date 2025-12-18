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

  // Labels lisibles pour les champs du cas patient
  const fieldLabels = {
    // Démographie
    age: "Âge",
    sex: "Sexe",
    // Profil temporel
    profile: "Profil temporel",
    onset: "Mode de début",
    duration_current_episode_hours: "Durée de l'épisode",
    intensity: "Intensité (EVA)",
    // Red flags
    fever: "Fièvre",
    meningeal_signs: "Signes méningés",
    neuro_deficit: "Déficit neurologique",
    seizure: "Crise d'épilepsie",
    htic_pattern: "Signes d'HTIC",
    // Contextes à risque
    pregnancy_postpartum: "Grossesse/Post-partum",
    pregnancy_trimester: "Trimestre de grossesse",
    trauma: "Traumatisme récent",
    recent_pl_or_peridural: "PL/Péridurale récente",
    immunosuppression: "Immunodépression",
    recent_pattern_change: "Changement récent de pattern",
    // Autres
    cancer_history: "Antécédent de cancer",
    vertigo: "Vertiges",
    tinnitus: "Acouphènes",
    visual_disturbance_type: "Troubles visuels",
    joint_pain: "Douleurs articulaires",
    horton_criteria: "Critères de Horton",
    first_episode: "Premier épisode",
    previous_workup: "Bilan antérieur",
    chronic_or_episodic: "Chronique ou épisodique",
    headache_location: "Localisation",
    headache_profile: "Type de céphalée",
    persistent_or_resolving: "Évolution",
    red_flag_context: "Contextes de red flags",
  };

  // Formate une valeur pour l'affichage
  const formatValue = (key, value) => {
    if (value === null || value === undefined) return <span style={{ color: "#999" }}>Non renseigné</span>;
    if (typeof value === "boolean") {
      return value ? <span style={{ color: "#dc3545" }}>Oui</span> : <span style={{ color: "#28a745" }}>Non</span>;
    }
    if (key === "sex") {
      const sexLabels = { M: "Masculin", F: "Féminin", Other: "Non précisé" };
      return sexLabels[value] || value;
    }
    if (key === "profile") {
      const profileLabels = { acute: "Aigu", subacute: "Subaigu", chronic: "Chronique", unknown: "Non déterminé" };
      return profileLabels[value] || value;
    }
    if (key === "onset") {
      const onsetLabels = { thunderclap: "Coup de tonnerre", progressive: "Progressif", chronic: "Chronique", unknown: "Non déterminé" };
      return onsetLabels[value] || value;
    }
    if (key === "duration_current_episode_hours" && typeof value === "number") {
      if (value < 24) return `${value} heures`;
      if (value < 168) return `${Math.round(value / 24)} jours`;
      if (value < 720) return `${Math.round(value / 168)} semaines`;
      return `${Math.round(value / 720)} mois`;
    }
    if (key === "intensity" && typeof value === "number") {
      return `${value}/10`;
    }
    if (key === "age" && typeof value === "number") {
      return `${value} ans`;
    }
    if (Array.isArray(value)) {
      return value.length > 0 ? value.join(", ") : <span style={{ color: "#999" }}>Aucun</span>;
    }
    return String(value);
  };

  // Vérifie si un champ a été réellement détecté (pas une valeur par défaut)
  const isFieldDetected = (log, fieldName) => {
    const detectedFields = log.extraction_metadata?.detected_fields || [];
    return detectedFields.includes(fieldName);
  };

  const renderLogContent = (log) => {
    const caseData = log.case_data || {};

    // Catégoriser les champs pour un affichage organisé
    const categories = {
      "Données démographiques": ["age", "sex"],
      "Profil temporel": ["profile", "onset", "duration_current_episode_hours", "intensity"],
      "Signes d'alarme (Red Flags)": ["fever", "meningeal_signs", "neuro_deficit", "seizure", "htic_pattern"],
      "Contextes à risque": ["pregnancy_postpartum", "trauma", "recent_pl_or_peridural", "immunosuppression", "recent_pattern_change"],
      "Informations complémentaires": ["cancer_history", "vertigo", "tinnitus", "visual_disturbance_type", "horton_criteria", "headache_location", "headache_profile"]
    };

    return (
      <div style={{ textAlign: "left" }}>
        <p><strong>Session ID:</strong> {log.session_id}</p>
        <p><strong>Messages échangés:</strong> {log.message_count}</p>

        {log.analysis && (
          <>
            <h4 style={{ marginTop: "15px", borderBottom: "2px solid #007bff", paddingBottom: "5px", color: "#007bff" }}>Analyse globale</h4>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "10px" }}>
              <p><strong>Red flags:</strong> <span style={{ color: log.analysis.has_red_flags ? "#dc3545" : "#28a745", fontWeight: "bold" }}>{log.analysis.has_red_flags ? "OUI" : "Non"}</span></p>
              <p><strong>Urgence:</strong> <span style={{ color: log.analysis.is_emergency ? "#dc3545" : "#28a745", fontWeight: "bold" }}>{log.analysis.is_emergency ? "OUI" : "Non"}</span></p>
            </div>
          </>
        )}

        <h4 style={{ marginTop: "20px", borderBottom: "2px solid #007bff", paddingBottom: "5px", color: "#007bff" }}>Cas patient extrait par NLU</h4>

        {Object.entries(categories).map(([categoryName, fields]) => {
          // Filtrer pour n'afficher que les champs qui ont une valeur significative ou qui ont été détectés
          const relevantFields = fields.filter(field => {
            const value = caseData[field];
            // Afficher si: valeur non nulle ET (valeur significative OU champ détecté)
            if (value === null || value === undefined) return false;
            if (field === "age" && value === 35 && !isFieldDetected(log, "age")) return false; // Masquer âge par défaut
            if (field === "sex" && value === "Other" && !isFieldDetected(log, "sex")) return false;
            if ((field === "onset" || field === "profile" || field === "headache_profile") && value === "unknown") return false;
            return true;
          });

          if (relevantFields.length === 0) return null;

          return (
            <div key={categoryName} style={{ marginTop: "15px" }}>
              <h5 style={{ margin: "0 0 8px 0", color: "#555", fontSize: "14px", borderBottom: "1px solid #eee", paddingBottom: "3px" }}>{categoryName}</h5>
              <div style={{ paddingLeft: "10px" }}>
                {relevantFields.map(field => (
                  <p key={field} style={{ margin: "4px 0", fontSize: "13px" }}>
                    <strong>{fieldLabels[field] || field}:</strong>{" "}
                    {formatValue(field, caseData[field])}
                    {isFieldDetected(log, field) && <span style={{ marginLeft: "5px", fontSize: "10px", color: "#28a745" }}>✓</span>}
                  </p>
                ))}
              </div>
            </div>
          );
        })}

        {log.asked_fields && log.asked_fields.length > 0 && (
          <>
            <h4 style={{ marginTop: "20px", borderBottom: "2px solid #6c757d", paddingBottom: "5px", color: "#6c757d" }}>Questions posées</h4>
            <ul style={{ marginTop: "10px", paddingLeft: "20px" }}>
              {log.asked_fields.map((f, i) => <li key={i} style={{ fontSize: "13px" }}>{fieldLabels[f] || f}</li>)}
            </ul>
          </>
        )}

        {log.extraction_metadata && log.extraction_metadata.detected_fields && log.extraction_metadata.detected_fields.length > 0 && (
          <>
            <h4 style={{ marginTop: "20px", borderBottom: "2px solid #6c757d", paddingBottom: "5px", color: "#6c757d" }}>Champs détectés par NLU</h4>
            <p style={{ fontSize: "12px", color: "#666", marginTop: "5px" }}>
              {log.extraction_metadata.detected_fields.map(f => fieldLabels[f] || f).join(", ")}
            </p>
            <p style={{ fontSize: "12px", color: "#666" }}>
              <strong>Confiance globale:</strong> {Math.round((log.extraction_metadata.overall_confidence || 0) * 100)}%
            </p>
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
