import type { ChatTransport, UIMessage, UIMessageChunk } from "ai";
import { command } from "./api";

export type ChatReceipt = {
  request_id: string;
  status: string;
  model_requested: string | null;
  model_observed: string | null;
  upstream_status: number | null;
  error?: string | null;
};
export type NativeChatEvent = {
  type: "text" | "finish" | "error";
  text?: string;
  code?: string;
  receipt?: ChatReceipt | null;
  http_status?: number | null;
};
type NativeCommand = (request: Record<string, unknown>) => Promise<unknown>;
const errors: Record<string, string> = {
  chat_invalid:
    "Conversation non prise en charge. Démarrez une nouvelle conversation texte.",
  chat_input_limit:
    "La conversation dépasse 64 messages ou 128 Kio. Démarrez une nouvelle conversation.",
  chat_output_limit:
    "La réponse dépasse la limite du playground (1 Mio). Elle est incomplète.",
  chat_route_changed:
    "Les réglages ou le modèle ont changé. Démarrez une nouvelle conversation pour utiliser la configuration actuelle.",
  chat_busy:
    "Une requête Chat se termine encore. Attendez sa fin avant une nouvelle conversation.",
  chat_expired:
    "Le transport Chat a été interrompu. Démarrez une nouvelle conversation.",
  chat_timeout:
    "Le délai de 120 secondes est dépassé. La réponse est incomplète.",
  chat_cancelled:
    "Génération arrêtée. La réponse partielle n’est pas une réponse complète.",
  chat_empty: "Le modèle n’a renvoyé aucun texte utile.",
  chat_length:
    "Le plafond de 4 096 tokens de sortie a été atteint. La réponse est incomplète.",
  chat_refused: "Le fournisseur a refusé cette génération.",
  chat_tools:
    "Le modèle demande un outil. Ce playground accepte uniquement les conversations texte.",
  chat_identity:
    "L’identité exacte du modèle n’a pas été confirmée par le fournisseur. Réponse non validée.",
  chat_http:
    "L’API a refusé la requête. Consultez le statut HTTP et le reçu dans l’inspecteur.",
  chat_incomplete: "Le flux s’est terminé sans réponse complète valide.",
  chat_unavailable:
    "Le moteur ou le fournisseur ne répond plus. Aucune relance automatique.",
};
export const chatError = (error: unknown) =>
  errors[error instanceof Error ? error.message : String(error)] ??
  errors.chat_unavailable;
const safeCode = (error: unknown) => {
  const code = error instanceof Error ? error.message : String(error);
  return code in errors ? code : "chat_unavailable";
};

/** IPC-only SDK transport. No provider fetch, key, retry or resumable stream. */
export class NativeChatTransport implements ChatTransport<UIMessage> {
  private cancelCurrent?: () => void;
  constructor(
    private readonly model: string,
    private readonly revision: number,
    private readonly native: NativeCommand = command,
    private readonly onResult: (result: NativeChatEvent) => void = () => {},
    private readonly interval = 40,
  ) {}

  reconnectToStream = async () => null;
  close = () => this.cancelCurrent?.();

  sendMessages: ChatTransport<UIMessage>["sendMessages"] = async (options) => {
    if (options.trigger !== "submit-message") throw new Error("chat_invalid");
    const messages = options.messages.map((message) => {
      if (
        !["user", "assistant"].includes(message.role) ||
        message.parts.some(
          (part) => part.type !== "text" && part.type !== "step-start",
        )
      )
        throw new Error("chat_invalid");
      return {
        role: message.role,
        content: message.parts
          .map((part) => (part.type === "text" ? part.text : ""))
          .join(""),
      };
    });
    const id = crypto.randomUUID();
    let aborted = options.abortSignal?.aborted ?? false;
    let consumerClosed = false;
    let nativeStarted = false;
    let terminal = false;
    let cancelSent = false;
    const cancelNative = () => {
      aborted = true;
      if (nativeStarted && !terminal && !cancelSent) {
        cancelSent = true;
        // The poll loop confirms the terminal native result, even after the
        // SDK has cancelled its reader. A lost IPC consumer also has a lease.
        void this.native({ command: "chat_cancel", id }).catch(() => {});
      }
    };
    this.cancelCurrent = cancelNative;
    options.abortSignal?.addEventListener("abort", cancelNative, {
      once: true,
    });
    return new ReadableStream<UIMessageChunk>({
      start: (controller) => {
        const enqueue = (chunk: UIMessageChunk) => {
          if (!consumerClosed && !aborted) controller.enqueue(chunk);
        };
        void (async () => {
          try {
            await this.native({
              command: "chat_start",
              id,
              session: options.chatId,
              model: this.model,
              revision: this.revision,
              messages,
            });
            nativeStarted = true;
            if (aborted) cancelNative();
            enqueue({ type: "start", messageId: id });
            enqueue({ type: "text-start", id: "text" });
            while (!terminal) {
              const batch = (await this.native({
                command: "chat_poll",
                id,
              })) as { events: NativeChatEvent[]; done: boolean };
              if (!Array.isArray(batch.events))
                throw new Error("chat_incomplete");
              for (const event of batch.events) {
                if (event.type === "text" && typeof event.text === "string") {
                  enqueue({
                    type: "text-delta",
                    id: "text",
                    delta: event.text,
                  });
                } else if (event.type === "finish" || event.type === "error") {
                  terminal = true;
                  const result: NativeChatEvent = aborted
                    ? { ...event, type: "error", code: "chat_cancelled" }
                    : event;
                  this.onResult(result);
                  if (result.type === "error")
                    throw new Error(safeCode(result.code));
                  enqueue({ type: "text-end", id: "text" });
                  enqueue({ type: "finish", finishReason: "stop" });
                } else throw new Error("chat_incomplete");
              }
              if (batch.done && !terminal) throw new Error("chat_incomplete");
              if (!terminal)
                await new Promise((resolve) =>
                  setTimeout(resolve, this.interval),
                );
            }
            if (!consumerClosed) controller.close();
          } catch (error) {
            const wasAborted = aborted;
            if (!terminal) {
              this.onResult({ type: "error", code: safeCode(error) });
              cancelNative();
            }
            if (!consumerClosed)
              controller.error(
                wasAborted
                  ? new DOMException("Stopped", "AbortError")
                  : new Error(safeCode(error)),
              );
          } finally {
            options.abortSignal?.removeEventListener("abort", cancelNative);
            if (this.cancelCurrent === cancelNative)
              this.cancelCurrent = undefined;
          }
        })();
      },
      cancel: () => {
        consumerClosed = true;
        cancelNative();
      },
    });
  };
}
