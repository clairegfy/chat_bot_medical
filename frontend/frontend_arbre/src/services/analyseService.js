import { API_BASE_URL } from "../config";

// Stocke le session_id pour maintenir le contexte côté serveur
let currentSessionId = null;

export async function analyserTexte(texte) {
  const response = await fetch(`${API_BASE_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message: texte,
      session_id: currentSessionId,
      history: []  // L'historique est géré côté serveur via session_id
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Erreur API (${response.status}) : ${errorText}`);
  }

  const data = await response.json();

  // Sauvegarder le session_id pour les prochains appels
  if (data.session_id) {
    currentSessionId = data.session_id;
  }

  return {
    decision: data.message,
    dialogueComplete: data.dialogue_complete,
    raw: data
  };
}

export function resetConversation() {
  currentSessionId = null;
}

export function getSessionId() {
  return currentSessionId;
}

export async function getPrescription(doctorName = "Dr. [NOM]") {
  if (!currentSessionId) {
    throw new Error("Aucune session active");
  }

  const response = await fetch(`${API_BASE_URL}/prescription`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      session_id: currentSessionId,
      doctor_name: doctorName
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Erreur API (${response.status}) : ${errorText}`);
  }

  return await response.text();
}

export async function getSessionLog() {
  if (!currentSessionId) {
    throw new Error("Aucune session active");
  }

  const response = await fetch(`${API_BASE_URL}/session-log/${currentSessionId}`);

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Erreur API (${response.status}) : ${errorText}`);
  }

  return await response.json();
}
