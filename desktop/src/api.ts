import { invoke } from "@tauri-apps/api/core";
export async function command<T>(request: Record<string, unknown>): Promise<T> {
  return invoke<T>("engine", { request });
}
export const saveSecret = (connection: string, secret: string) =>
  invoke("save_secret", { connection, secret });
const messages: Record<string, string> = {
  subscription_busy:
    "Une connexion Codex est déjà en cours. Terminez-la ou annulez-la.",
  subscription_expired: "La connexion Codex a expiré. Reconnectez le compte.",
  subscription_failed:
    "La connexion au compte n’a pas abouti. Vous pouvez recommencer sans relancer de génération.",
  portal_unavailable:
    "Le connecteur Hermes n’est pas disponible. Nous Portal nécessite Hermes installé sur cet appareil.",
  portal_port_in_use:
    "Le port du connecteur Nous Portal est déjà utilisé. Aucun autre service n’a été arrêté.",
  browser_unavailable:
    "Le navigateur n’a pas pu s’ouvrir. Ouvrez l’adresse de connexion affichée ici et utilisez le code.",
  invalid_decision:
    "Le décideur n’a pas renvoyé une décision valide. Aucun modèle n’a été lancé.",
  quality_requirement_unavailable:
    "Aucun modèle disponible n’atteint le niveau requis pour ce profil. Vérifiez le classement et les modèles actifs.",
  no_compatible_candidates:
    "Aucun modèle actif n’est compatible avec ce profil.",
  credential_destination_changed:
    "Cette destination utilise un identifiant de connexion existant. Créez une nouvelle connexion (nouvel UUID dans le fichier) pour ne pas réutiliser sa clé sur un autre serveur.",
  catalogue_too_large:
    "Ce catalogue dépasse la limite de 4 096 modèles. Aucune liste partielle n’a été importée ; filtrez le catalogue côté serveur.",
  config_file_unavailable:
    "Le fichier de configuration est inaccessible. Vérifiez le chemin et les droits ; les réglages actifs sont conservés.",
  configuration_conflict:
    "Le fichier ou les réglages ont changé. Chargez le fichier ou abandonnez le brouillon avant de réessayer.",
  invalid_config:
    "Configuration refusée. Vérifiez les champs, les limites et l’URL API.",
  engine_unavailable:
    "Le moteur embarqué est indisponible. Réinstallez le paquet complet.",
  engine_disconnected:
    "Le moteur ne répond plus. Les données affichées ne sont plus à jour.",
  engine_already_running:
    "Un moteur OMR utilise déjà ce dossier. Revenez à la fenêtre existante.",
  vault_unavailable:
    "Impossible de vérifier l’enregistrement dans le coffre OS.",
  generation_failed:
    "La génération a échoué. Consultez le reçu dans l’inspecteur.",
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
  upstream_unavailable:
    "L’API ne répond pas ou a refusé la requête. Aucune relance automatique.",
  requests_active:
    "Des requêtes sont en cours. Attendez leur fin ou confirmez un arrêt forcé.",
  incompatible_protocol:
    "Ce parcours ne prend pas en charge le protocole du modèle.",
  consent_required: "Confirmez cette action avant de la lancer.",
  decider_not_configured:
    "Choisissez un décideur et autorisez sa destination exacte. Le mode direct reste disponible.",
  managed_not_running:
    "Le décideur local est arrêté. Démarrez le modèle géré avant le test.",
  managed_busy:
    "Une opération du modèle géré est déjà en cours. Attendez ou annulez-la.",
  managed_integrity_failed:
    "Les fichiers du modèle ne correspondent pas aux empreintes attendues. Aucun checkpoint partiel n’a été activé.",
  managed_download_failed:
    "Le téléchargement a échoué. Réessayez explicitement ; aucun fichier partiel n’est activé.",
  managed_runtime_unavailable:
    "Le modèle local n’a pas pu démarrer. Vérifiez que le paquet inclut le runtime ONNX.",
  decision_context_rejected:
    "Ce contexte n’est pas pris en charge par le décideur local (texte seul, 1024 tokens maximum).",
};
export function errorMessage(error: unknown) {
  return (
    messages[String(error)] ??
    "Action impossible. Vérifiez les réglages et l’état du moteur."
  );
}
