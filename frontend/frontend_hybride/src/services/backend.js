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

export async function getPrescription(session_id, doctor_name = "Dr. [NOM]") {
  const res = await fetch(`${API_URL}/prescription`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id, doctor_name }),
  });

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Erreur lors de la génération de l'ordonnance");
  }

  return res.text();
}

export async function getSessionLog(session_id) {
  const res = await fetch(`${API_URL}/session-log/${session_id}`);

  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || "Erreur lors de la récupération des logs");
  }

  return res.json();
}

