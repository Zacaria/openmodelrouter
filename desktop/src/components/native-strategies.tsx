import { useState } from "react";
import { Badge, Button, Card, Field, Switch, Select } from "./ui";
import type { NativeState } from "../types";
import { useErrorToast } from "../notifications";

const statuses: Record<string, string> = {
  disconnected: "Déconnectée",
  connecting: "Connexion en cours",
  ready: "Prête",
  running: "Opération en cours",
};
export function NativeStrategies({
  state,
  run,
}: {
  state: NativeState;
  run: (request: Record<string, unknown>) => Promise<void>;
}) {
  const [consent, setConsent] = useState(false);
  const [context, setContext] = useState("");
  const [instructions, setInstructions] = useState("");
  const [prompt, setPrompt] = useState("");
  const [model, setModel] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const displayError =
    error ||
    (state.error
      ? state.error === "native_cancelled"
        ? "Opération annulée. Vous pouvez reprendre la session."
        : state.error === "native_timeout"
          ? "Délai dépassé : session fermée. Reconnectez une nouvelle session."
          : "L’opération native a échoué. Aucun succès n’est attesté. Fermez la session avant de vous reconnecter."
      : "");
  useErrorToast(displayError);
  const connected = state.models.length > 0;
  const ready = connected && !state.active && !sending;
  const available = state.availability.codex === "installed_unverified";
  const send = async (action: string) => {
    setSending(true);
    setError("");
    try {
      await run({
        action,
        ...(action === "connect" ? { consent, context, instructions } : {}),
        ...(["maintain", "switch", "delegate"].includes(action)
          ? { prompt }
          : {}),
        ...(action === "switch" ? { model: model || state.model } : {}),
      });
      if (action === "connect") {
        setConsent(false);
        setContext("");
        setInstructions("");
      }
      if (action === "close") setPrompt("");
    } catch {
      setError(
        "Commande refusée. Vérifiez l’état de la session avant de réessayer.",
      );
    } finally {
      setSending(false);
    }
  };
  return (
    <>
      <Card>
        <div className="section-heading">
          <h2>Nouvelle session Codex</h2>
          <Badge>{statuses[state.status] || state.status}</Badge>
        </div>
        <p>
          Compacter ou déléguer dans une session appartenant à OMR. Le routage
          API direct reste inchangé ; aucune session existante n’est ouverte.
        </p>
        <p className="muted">
          Codex 0.159.0 · Linux x86_64 · Bubblewrap · souscription ChatGPT
          native. Outils externes désactivés, permissions read-only / never.
          Seul read_context peut lire le contexte saisi ici.
        </p>
        {!connected && (
          <>
            {!available && (
              <p role="status">
                Non disponible : installez Codex 0.159.0 et Bubblewrap sur Linux
                x86_64, puis connectez Codex à votre souscription.
                L’authentification reste gérée par Codex.
              </p>
            )}
            <Field label="Instructions de session">
              <textarea
                aria-label="Instructions de session"
                maxLength={32000}
                rows={3}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                disabled={state.active}
              />
            </Field>
            <p className="muted">
              Langue, format et consignes à conserver entre les modèles. Ces
              instructions restent distinctes des données ci-dessous et ne
              peuvent pas élargir les permissions.
            </p>
            <Field label="Contexte à transmettre à la nouvelle session">
              <textarea
                aria-label="Contexte natif"
                maxLength={32000}
                rows={4}
                value={context}
                onChange={(e) => setContext(e.target.value)}
                disabled={state.active}
              />
            </Field>
            <Switch
              checked={consent}
              onCheckedChange={setConsent}
              label="J’autorise l’utilisation de ma souscription native pour les commandes explicites de cette session."
            />
            <Button
              disabled={!available || !consent || state.active || sending}
              onClick={() => void send("connect")}
            >
              Connecter une session isolée
            </Button>
          </>
        )}
        {connected && (
          <>
            <Field label="Instruction du prochain tour">
              <textarea
                aria-label="Instruction native"
                maxLength={32000}
                rows={4}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={state.active}
              />
            </Field>
            <Field label="Modèle du prochain changement">
              <Select
                value={model || state.model || ""}
                disabled={!ready}
                onValueChange={setModel}
                options={state.models.map((value) => ({ value, label: value }))}
              />
            </Field>
            <p>
              Modèle demandé : <code>{state.model}</code> · effort low. Le choix
              du modèle enfant n’est pas garanti.
            </p>
            <div className="revision-list">
              <Button
                disabled={!ready || !prompt.trim()}
                onClick={() => void send("maintain")}
              >
                Continuer sans changer
              </Button>
              <Button
                variant="secondary"
                disabled={!ready || !prompt.trim()}
                onClick={() => void send("switch")}
              >
                Changer et envoyer
              </Button>
              <Button
                variant="secondary"
                disabled={!ready}
                onClick={() => void send("compact")}
              >
                Compacter le contexte
              </Button>
              <Button
                variant="secondary"
                disabled={!ready || !prompt.trim()}
                onClick={() => void send("delegate")}
              >
                Déléguer à un enfant
              </Button>
              <Button
                variant="destructive"
                disabled={!ready}
                onClick={() => void send("close")}
              >
                Fermer et effacer la session
              </Button>
            </div>
          </>
        )}
        {state.active && (
          <Button
            variant="destructive"
            disabled={sending || state.cancel_requested}
            onClick={() => void send("cancel")}
          >
            {state.cancel_requested
              ? "Annulation demandée · attente de terminaison"
              : "Demander l’annulation"}
          </Button>
        )}
        {state.status === "connecting" && (
          <p>
            Vérification du compte et du catalogue natifs. La connexion seule ne
            génère aucun texte.
          </p>
        )}
        {(error || state.error) && (
          <p className="inline-error" role="alert">
            {displayError}
          </p>
        )}
        <p className="muted">
          Coûts auxiliaires et facture non mesurés. Les compteurs natifs sont
          consultables dans l’inspecteur, séparément des totaux API. Chaque
          génération peut consommer le quota de votre souscription.
        </p>
        <p className="muted">
          OMR garde le contexte et la réponse en mémoire. Codex écrit
          l’historique de cette session dans un dossier temporaire sur disque,
          effacé à la fermeture normale de la session. OMR n’exporte pas ce
          transcript. Ces fichiers ne sont pas chiffrés par OMR ; un crash peut
          les laisser sur disque. Fermer la fenêtre laisse le moteur actif.
        </p>
        {state.reply && (
          <section aria-label="Dernier résultat natif">
            <h3>Dernier résultat</h3>
            <pre className="native-reply">{state.reply}</pre>
          </section>
        )}
      </Card>
      <Card>
        <h2>Disponibilités des clients</h2>
        <dl className="detail-grid">
          <div>
            <dt>Codex · Linux</dt>
            <dd>
              {connected
                ? "Session isolée connectée"
                : available
                  ? "Installé · accès fournisseur non vérifié"
                  : "Non disponible"}
            </dd>
          </div>
          <div>
            <dt>Claude Code</dt>
            <dd>
              Non disponible · délégation sémantique et permissions enfant non
              qualifiées
            </dd>
          </div>
          <div>
            <dt>OMP</dt>
            <dd>
              Non disponible · préservation des outils et délégation non
              qualifiées
            </dd>
          </div>
          <div>
            <dt>Hermes / autres OS</dt>
            <dd>Non disponible · parcours intégré non qualifié</dd>
          </div>
        </dl>
      </Card>
    </>
  );
}
