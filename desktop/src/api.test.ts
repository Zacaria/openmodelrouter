import { describe, expect, it } from "vitest";
import { errorMessage } from "./api";

describe("generation diagnostic messages", () => {
  const messages = {
    generation_budget_exhausted:
      "Le test a atteint son plafond de sortie sans réponse complète. La génération n’est pas vérifiée.",
    generation_incomplete:
      "Le fournisseur a renvoyé une réponse incomplète. La génération n’est pas vérifiée.",
    generation_refused:
      "Le modèle a refusé la demande de test. La génération n’est pas vérifiée.",
    generation_empty:
      "Le modèle n’a renvoyé aucun texte exploitable. La génération n’est pas vérifiée.",
    generation_identity_mismatch:
      "L’identité du modèle reçu ne correspond pas au modèle demandé. La génération n’est pas vérifiée.",
    generation_upstream_rejected:
      "Le fournisseur a rejeté la requête de test. Consultez le reçu pour le statut HTTP.",
    generation_timeout:
      "Le test a dépassé son délai. Aucun nouvel essai n’est lancé automatiquement.",
    generation_cancelled:
      "Le test a été annulé. La génération n’est pas vérifiée.",
    generation_unavailable:
      "Le test a rencontré une erreur de transport ou de serveur. Consultez le reçu.",
  };
  it.each(Object.entries(messages))(
    "explains %s without guessing a billing or credential cause",
    (code, message) => {
      expect(errorMessage(code)).toBe(message);
    },
  );
  it("does not echo arbitrary upstream text", () => {
    expect(errorMessage("untrusted provider body")).not.toContain(
      "untrusted provider body",
    );
  });
});
