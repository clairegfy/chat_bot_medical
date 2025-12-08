import { API_BASE_URL } from "../config";

export async function analyserTexte(texte) {
  const response = await fetch(`${API_BASE_URL}/analyse`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texte }),
  });

  if (!response.ok) {
    // ici tu recevrais encore {"detail": "Not Found"} si l'URL est mauvaise
    const errorText = await response.text();
    throw new Error(`Erreur API (${response.status}) : ${errorText}`);
  }
  
  return await response.json();
}
