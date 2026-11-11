import { useEffect, useMemo, useRef, useState } from "react";
import { useChat } from "@ai-sdk/react";
import { errorMessage } from "./api";
import { useErrorToast } from "./notifications";
import { Select as SelectPrimitive } from "radix-ui";
import { ChevronDown, MessageSquare, Send, Square } from "lucide-react";
import { Button, Field } from "./components/ui";
import {
  NativeChatTransport,
  chatError,
  type NativeChatEvent,
} from "./chat-transport";
import type { Config } from "./types";
import "./chat.css";

type ChatModel = { route: string; upstream: string; protocol: string };
export function chatRoutes(config: Config) {
  const groups = config.connections
    .map((connection) => ({
      id: connection.id,
      name: connection.name,
      models: connection.models
        .filter((model) => model.enabled)
        .map((model) => ({
          route: `direct/${connection.id}/${model.id}`,
          upstream: model.upstream,
          protocol:
            ["chat", "responses", "anthropic"].find((p) =>
              model.protocols.includes(p),
            ) ?? "",
        }))
        .filter((model) => model.protocol),
    }))
    .filter((group) => group.models.length);
  const protocol = ["chat", "responses", "anthropic"].find((p) =>
    config.connections.some((c) =>
      c.models.some((m) => m.enabled && m.protocols.includes(p)),
    ),
  );
  if (config.decider?.consent && protocol)
    groups.unshift({
      id: "omr/profiles",
      name: "OMR",
      models: [
        ["economy", "Économie"],
        ["balanced", "Équilibré"],
        ["quality", "Qualité"],
      ].map(([profile, name]) => ({
        route: `omr/${profile}`,
        upstream: name,
        protocol,
      })),
    });
  return groups;
}

export function ChatPlayground({
  config,
  revision,
}: {
  config: Config;
  revision: number;
}) {
  const groups = chatRoutes(config);
  const [selection, setSelection] = useState<{
    model: ChatModel;
    provider: string;
  } | null>(null);
  const [generation, setGeneration] = useState(0);
  const [busy, setBusy] = useState(false);
  const choose = (route: string) => {
    for (const group of groups) {
      const model = group.models.find((m) => m.route === route);
      if (model) {
        setSelection({ model, provider: group.name });
        setGeneration((n) => n + 1);
        return;
      }
    }
  };
  return (
    <section className="panel chat-panel" aria-label="Playground Chat">
      <h2>Conversation</h2>
      <p className="warning">
        Chaque envoi transmet la conversation au modèle sélectionné et, en
        routage automatique, au décideur configuré. Votre accès peut être
        facturé. Aucun historique n’est enregistré. Changer de modèle ou de
        profil efface la conversation.
      </p>
      {!groups.length ? (
        <div className="empty">
          <MessageSquare size={32} />
          <h3>Aucun modèle activé</h3>
          <p>Activez un modèle dans Fournisseurs pour commencer.</p>
        </div>
      ) : (
        <>
          <div className="chat-toolbar">
            <Field label="Modèle du Chat">
              <SelectPrimitive.Root
                value={selection?.model.route ?? ""}
                onValueChange={choose}
                disabled={busy}
              >
                <SelectPrimitive.Trigger
                  className="select-trigger"
                  aria-label="Modèle du Chat"
                >
                  <SelectPrimitive.Value placeholder="Choisir un modèle" />
                  <SelectPrimitive.Icon>
                    <ChevronDown size={14} />
                  </SelectPrimitive.Icon>
                </SelectPrimitive.Trigger>
                <SelectPrimitive.Portal>
                  <SelectPrimitive.Content
                    className="select-content"
                    position="popper"
                    sideOffset={5}
                  >
                    <SelectPrimitive.Viewport>
                      {groups.map((group) => (
                        <SelectPrimitive.Group key={group.id}>
                          <SelectPrimitive.Label className="chat-provider-label">
                            {group.name}
                          </SelectPrimitive.Label>
                          {group.models.map((model) => (
                            <SelectPrimitive.Item
                              className="select-item"
                              key={model.route}
                              value={model.route}
                            >
                              <SelectPrimitive.ItemText>
                                {group.name} · {model.upstream}
                              </SelectPrimitive.ItemText>
                            </SelectPrimitive.Item>
                          ))}
                        </SelectPrimitive.Group>
                      ))}
                    </SelectPrimitive.Viewport>
                  </SelectPrimitive.Content>
                </SelectPrimitive.Portal>
              </SelectPrimitive.Root>
            </Field>
            <Button
              disabled={busy || !selection}
              onClick={() => setGeneration((n) => n + 1)}
            >
              Nouvelle conversation
            </Button>
          </div>
          {selection ? (
            <ChatConversation
              key={`${selection.model.route}/${generation}`}
              model={selection.model}
              provider={selection.provider}
              revision={revision}
              available={groups.some((g) =>
                g.models.some((m) => m.route === selection.model.route),
              )}
              onBusy={setBusy}
            />
          ) : (
            <div className="empty">
              <MessageSquare size={32} />
              <h3>Choisissez un modèle</h3>
              <p>
                Le texte reste en mémoire jusqu’à la fermeture du Chat ou une
                nouvelle conversation.
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ChatConversation({
  model,
  provider,
  revision,
  available,
  onBusy,
}: {
  model: ChatModel;
  provider: string;
  revision: number;
  available: boolean;
  onBusy: (busy: boolean) => void;
}) {
  const [session] = useState(() => crypto.randomUUID());
  const [pinnedRevision] = useState(revision);
  const [input, setInput] = useState("");
  const [result, setResult] = useState<NativeChatEvent | null>(null);
  const [stopping, setStopping] = useState(false);
  const [sealed, setSealed] = useState(false);
  const transport = useMemo(
    () =>
      new NativeChatTransport(
        model.route,
        pinnedRevision,
        undefined,
        (event) => {
          setResult(event);
          setStopping(false);
          if (event.type === "error") setSealed(true);
        },
      ),
    [model.route, pinnedRevision],
  );
  const { messages, sendMessage, status, stop, error } = useChat({
    id: session,
    transport,
  });
  const active = status === "submitted" || status === "streaming";
  const busy = active || stopping;
  const changed = revision !== pinnedRevision || !available;
  useErrorToast(
    result?.type === "error"
      ? result.receipt?.error
        ? errorMessage(result.receipt.error)
        : chatError(result.code)
      : error
        ? chatError(error)
        : changed
          ? "La configuration a changé. Démarrez une nouvelle conversation pour utiliser les réglages actuels."
          : "",
  );
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    onBusy(busy);
  }, [busy, onBusy]);
  useEffect(
    () => () => {
      transport.close();
    },
    [transport],
  );
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [messages]);
  const send = () => {
    if (!input.trim() || busy || sealed || changed) return;
    const text = input;
    setInput("");
    setResult(null);
    void sendMessage({ text });
  };
  const stopGeneration = () => {
    setStopping(true);
    setSealed(true);
    void stop();
    transport.close();
  };
  return (
    <div className="chat-conversation">
      <div className="chat-destination">
        <strong>
          {provider} · {model.upstream}
        </strong>
        <code>{model.route}</code>
        <small>
          {model.protocol} · 4 096 tokens de sortie maximum · 120 s maximum
        </small>
        {model.route.startsWith("omr/") && (
          <small>
            Le profil choisit un modèle compatible avec {model.protocol}. Le
            modèle utilisé est confirmé à la fin du tour.
          </small>
        )}
      </div>
      {changed && (
        <p role="alert" className="warning">
          La configuration a changé. Démarrez une nouvelle conversation pour
          utiliser les réglages actuels.
        </p>
      )}
      <ol className="chat-messages" aria-label="Conversation">
        {!messages.length && (
          <li className="muted">
            Écrivez un premier message pour tester cet accès.
          </li>
        )}
        {messages.map((message) => (
          <li key={message.id} className={`chat-message chat-${message.role}`}>
            <strong>{message.role === "user" ? "Vous" : "Modèle"}</strong>
            <div>
              {message.parts
                .map((part) => (part.type === "text" ? part.text : ""))
                .join("")}
            </div>
          </li>
        ))}
      </ol>
      <div ref={end} />
      <div className="chat-status" role="status" aria-live="polite">
        {stopping
          ? "Arrêt demandé au moteur…"
          : active
            ? status === "streaming"
              ? "Réponse en cours…"
              : "Connexion au modèle…"
            : result?.type === "finish"
              ? "Réponse terminée · identité confirmée"
              : result?.type === "error"
                ? result.receipt?.error
                  ? errorMessage(result.receipt.error)
                  : chatError(result.code)
                : error
                  ? chatError(error)
                  : sealed
                    ? "Conversation arrêtée. Démarrez une nouvelle conversation."
                    : ""}
      </div>
      {result?.receipt && (
        <div className="chat-receipt">
          <span>
            Reçu : <code>{result.receipt.request_id}</code>
          </span>
          {result.type === "finish" && (
            <span>
              Modèle confirmé : <code>{result.receipt.model_observed}</code>
            </span>
          )}
          <span>
            Transport : {result.receipt.status}
            {result.http_status ? ` · HTTP ${result.http_status}` : ""}
          </span>
          {result.receipt.error && (
            <span>
              Motif : <code>{result.receipt.error}</code>
            </span>
          )}
        </div>
      )}
      {result?.type === "error" && result.http_status && !result.receipt && (
        <p>HTTP {result.http_status}</p>
      )}
      {(sealed || status === "error") && (
        <p className="warning">
          Réponse non validée. Démarrez une nouvelle conversation avant un
          nouvel envoi.
        </p>
      )}
      <form
        className="chat-composer"
        onSubmit={(event) => {
          event.preventDefault();
          send();
        }}
      >
        <label htmlFor={`chat-input-${session}`}>
          Message pour {model.upstream}
        </label>
        <textarea
          id={`chat-input-${session}`}
          value={input}
          onChange={(event) => setInput(event.target.value)}
          maxLength={128 * 1024}
          rows={3}
          disabled={busy || sealed || changed || status === "error"}
          placeholder="Écrivez votre message…"
        />
        <div className="actions">
          {active || stopping ? (
            <Button
              type="button"
              variant="destructive"
              disabled={stopping}
              onClick={stopGeneration}
            >
              <Square size={14} />
              Arrêter
            </Button>
          ) : (
            <Button
              type="submit"
              variant="default"
              disabled={
                !input.trim() || sealed || changed || status === "error"
              }
            >
              <Send size={14} />
              Envoyer
            </Button>
          )}
          <small>Texte uniquement · aucun repli ni relance automatique</small>
        </div>
      </form>
    </div>
  );
}
