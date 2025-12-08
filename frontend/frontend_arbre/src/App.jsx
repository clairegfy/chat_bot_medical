// src/App.jsx
import { useState } from "react";
import "./index.css";
import { analyserTexte } from "./services/analyseService";

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const sendMessage = async () => {
    if (!input.trim()) return;

    // message utilisateur
    setMessages((prev) => [...prev, { role: "user", text: input }]);

    try {
      const data = await analyserTexte(input);

      const responseText =
        `🧠 Décision médicale :\n${data.decision}\n\n` +
        `📋 Contre-indications :\n${data.contraindications}`;

      setMessages((prev) => [...prev, { role: "bot", text: responseText }]);
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
        Saisissez un cas clinique pour obtenir une recommandation d’imagerie.
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
    </div>
  );
}
