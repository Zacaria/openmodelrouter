import { useCallback, useEffect, useRef, useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { command, errorMessage, saveSecret } from "./api";
import { useErrorToast } from "./notifications";
import { Button } from "./components/ui";
import type { Connection } from "./types";

type Login = { status: string; auth?: { url: string; code: string } | null };
type Portal = {
  logging_in: boolean;
  running: boolean;
  login: number | null;
  auth?: Login["auth"];
  error?: string;
};

export function SubscriptionAccess({
  connection,
  disabled,
}: {
  connection: Connection;
  disabled: boolean;
}) {
  const [login, setLogin] = useState<Login>({ status: "idle" });
  const [portal, setPortal] = useState<Portal>();
  const [error, setError] = useState("");
  const [pollError, setPollError] = useState("");
  const [working, setWorking] = useState(false);
  const codex = connection.subscription === "codex";
  const backend = codex ? "subscription" : "portal";
  const requestId = useRef(0);
  const browserRequestId = useRef(0);
  const openOnAuth = useRef(false);
  useEffect(
    () => () => {
      requestId.current += 1;
      openOnAuth.current = false;
    },
    [backend, connection.id],
  );
  const openBrowser = useCallback(async () => {
    const request = requestId.current;
    const browserRequest = ++browserRequestId.current;
    openOnAuth.current = false;
    setError("");
    try {
      await invoke("open_subscription_login", { connection: connection.id });
    } catch (cause) {
      if (
        request === requestId.current &&
        browserRequest === browserRequestId.current
      )
        setError(errorMessage(cause));
    }
  }, [connection.id]);
  async function run(action: string) {
    const request = ++requestId.current;
    openOnAuth.current = false;
    setWorking(true);
    setError("");
    try {
      const value = await command({
        command: backend,
        connection: connection.id,
        action,
      });
      if (request !== requestId.current) return;
      openOnAuth.current = codex ? action === "start" : action === "login";
      setPollError("");
      if (codex) setLogin(value as Login);
      else setPortal(value as Portal);
    } catch (cause) {
      if (request === requestId.current) setError(errorMessage(cause));
    } finally {
      if (request === requestId.current) {
        requestId.current += 1;
        setWorking(false);
      }
    }
  }
  useEffect(() => {
    const auth = codex
      ? login?.status === "waiting" && login.auth
      : portal?.logging_in && !portal.error && portal.auth;
    if (!disabled && !pollError && openOnAuth.current && auth)
      void openBrowser();
  }, [openBrowser, codex, disabled, login, portal, pollError]);
  useEffect(() => {
    if (disabled) return;
    let alive = true;
    let polling = false;
    async function poll() {
      if (polling) return;
      polling = true;
      const request = requestId.current;
      try {
        const value = await command({
          command: backend,
          connection: connection.id,
          action: "status",
        });
        if (alive && request === requestId.current) {
          setPollError("");
          if (codex) setLogin(value as Login);
          else setPortal(value as Portal);
        }
      } catch (cause) {
        if (alive && request === requestId.current)
          setPollError(errorMessage(cause));
      } finally {
        polling = false;
      }
    }
    void poll();
    const timer = setInterval(() => void poll(), 2000);
    return () => {
      alive = false;
      clearInterval(timer);
    };
  }, [backend, codex, connection.id, disabled]);
  const waiting = ["starting", "waiting", "authenticated"].includes(
    login.status,
  );
  useErrorToast(
    pollError ||
      error ||
      (portal?.error ? errorMessage(portal.error) : "") ||
      (login.status === "expired"
        ? "Connexion expirée. Reconnectez le compte."
        : login.status === "failed"
          ? "La connexion a échoué. Vous pouvez recommencer."
          : ""),
  );
  return (
    <div
      className="stack"
      aria-label={codex ? "Connexion Codex" : "Connexion Nous Portal"}
    >
      {(pollError || error) && <p role="alert">{pollError || error}</p>}
      {codex ? (
        <>
          <p>
            Connectez votre compte ChatGPT pour utiliser Codex. OMR ouvre une
            connexion dédiée ; vos sessions Codex et oh-my-pi existantes ne sont
            pas importées.
          </p>
          {!pollError && (
            <p role="status">
              {(
                {
                  idle: "Compte à connecter",
                  starting: "Préparation de la connexion…",
                  waiting: "Terminez la connexion dans votre navigateur.",
                  authenticated: "Enregistrement dans le coffre OS…",
                  connected:
                    "Compte connecté. Découvrez les modèles disponibles.",
                  expired: "Connexion expirée. Reconnectez le compte.",
                  failed: "La connexion a échoué. Vous pouvez recommencer.",
                  cancelled: "Connexion annulée.",
                } as Record<string, string>
              )[login.status] ?? "État de connexion inconnu"}
            </p>
          )}
          {!pollError && login.auth && (
            <p>
              Code à saisir sur auth.openai.com : <code>{login.auth.code}</code>{" "}
              <Button variant="secondary" onClick={() => void openBrowser()}>
                Ouvrir la connexion
              </Button>
            </p>
          )}
          <div className="actions">
            <Button
              disabled={disabled || working || waiting}
              onClick={() => void run("start")}
            >
              {login.status === "connected"
                ? "Changer de compte Codex"
                : "Connecter Codex"}
            </Button>
            {waiting && (
              <Button
                variant="ghost"
                disabled={working}
                onClick={() => void run("cancel")}
              >
                Annuler la connexion
              </Button>
            )}
            {login.status === "connected" && (
              <Button
                variant="ghost"
                disabled={disabled || working}
                onClick={() => {
                  setWorking(true);
                  void saveSecret(connection.id, "")
                    .then(() => setLogin({ status: "idle" }))
                    .catch((e) => setError(errorMessage(e)))
                    .finally(() => setWorking(false));
                }}
              >
                Retirer cet accès d’OMR
              </Button>
            )}
          </div>
        </>
      ) : (
        <>
          <p>
            Le connecteur Hermes doit être installé sur cet appareil. OMR
            l’utilise dans un espace dédié pour votre abonnement Nous Portal,
            sans changer vos réglages Hermes habituels. Aucune clé API Portal
            n’est à coller ici.
          </p>
          {!pollError && (
            <p role="status">
              {portal?.logging_in
                ? "Ouvrez la page de connexion et saisissez le code si demandé."
                : portal?.login === 0
                  ? "Connexion enregistrée par Hermes."
                  : portal?.login != null
                    ? "La connexion n’a pas abouti. Recommencez."
                    : "Connectez votre abonnement, puis démarrez le connecteur."}
              {portal?.running
                ? " Connecteur local démarré ; découvrez le catalogue pour vérifier l’accès."
                : ""}
            </p>
          )}
          {!pollError && portal?.error && (
            <p role="alert">{errorMessage(portal.error)}</p>
          )}
          {!pollError && portal?.auth && (
            <div className="stack">
              <p>
                Adresse de connexion :{" "}
                <code style={{ overflowWrap: "anywhere" }}>
                  {portal.auth.url}
                </code>
              </p>
              <p>
                Code à saisir : <code>{portal.auth.code}</code>
              </p>
              <Button variant="secondary" onClick={() => void openBrowser()}>
                Ouvrir la connexion Nous Portal
              </Button>
            </div>
          )}
          <div className="actions">
            <Button
              disabled={disabled || working || portal?.logging_in}
              onClick={() => void run("login")}
            >
              Connecter Nous Portal
            </Button>
            <Button
              variant="secondary"
              disabled={
                disabled || working || portal?.running || portal?.logging_in
              }
              onClick={() => void run("start")}
            >
              Démarrer le connecteur
            </Button>
            {portal?.logging_in && (
              <Button
                variant="ghost"
                disabled={working}
                onClick={() => void run("cancel")}
              >
                Annuler la connexion
              </Button>
            )}
            {portal?.running && (
              <Button
                variant="ghost"
                disabled={working}
                onClick={() => void run("stop")}
              >
                Arrêter le connecteur
              </Button>
            )}
          </div>
        </>
      )}
      <p className="muted">
        La connexion ne lance aucune génération. Les tests et les tâches
        utilisent les limites de votre abonnement.
      </p>
    </div>
  );
}
