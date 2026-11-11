import { useEffect, useState } from "react";
import { Button, Card, Field, Input, Switch, Badge, Select } from "./ui";
import { command, errorMessage, saveSecret } from "../api";
import { useErrorToast } from "../notifications";
import type { Config, Connection, Snapshot } from "../types";

export const CHECKPOINT = "s1d1-dac13b5";
const PROGRESS_KEY = "omr:onboarding:v1";
export function readOnboarding(): { open: boolean; step: number } | null {
  try {
    const value = JSON.parse(localStorage.getItem(PROGRESS_KEY) ?? "null");
    return value &&
      typeof value.open === "boolean" &&
      Number.isInteger(value.step) &&
      value.step >= 0 &&
      value.step <= 3
      ? { open: value.open, step: value.step }
      : null;
  } catch {
    return null;
  }
}
export function writeOnboarding(
  open: boolean,
  step = readOnboarding()?.step ?? 0,
) {
  try {
    localStorage.setItem(PROGRESS_KEY, JSON.stringify({ open, step }));
  } catch {
    /* Config persistence remains authoritative if WebView storage is unavailable. */
  }
}
export function deciderTarget(config?: Config) {
  const d = config?.decider;
  if (!d) return null;
  if (d.mode === "managed") return { mode: "managed", model: d.model };
  const c = config?.connections.find((value) => value.id === d.connection);
  return c
    ? {
        connection: c.id,
        url: c.url,
        model: d.model,
        ...(d.mode ? { mode: d.mode } : {}),
        ...(d.protocol ? { protocol: d.protocol } : {}),
      }
    : null;
}
export function needsOnboarding(config: Config) {
  return !config.connections.some((c) => c.models.some((m) => m.enabled));
}
export function initialStep(config: Config) {
  return needsOnboarding(config) ? 0 : config.decider?.consent ? 2 : 1;
}
type Grant = ReturnType<typeof deciderTarget>;
type Persist = (config: Config, grant?: Grant) => Promise<boolean>;
const managedNames: Record<string, string> = {
  absent: "Non téléchargé",
  downloading: "Téléchargement en cours",
  installed: "Installé · arrêté",
  starting: "Chargement en cours",
  ready: "Prêt",
  stopped: "Arrêté",
  cancelled: "Annulé",
  cancelling: "Annulation en cours",
  error: "Échec",
};

export function DeciderPanel({
  config,
  state,
  busy,
  change,
  grant,
  act,
}: {
  config: Config;
  state: Snapshot;
  busy: boolean;
  change: (config: Config) => void;
  grant: (target: Grant) => void;
  act: <T>(
    action: () => Promise<T>,
    success?: string,
  ) => Promise<T | undefined>;
}) {
  const d = config.decider;
  const [downloadConsent, setDownloadConsent] = useState(false);
  const mode = d?.mode ?? (d ? "server" : "none");
  const managed = state.managed;
  const setMode = (value: string) =>
    change({
      ...config,
      decider:
        value === "none"
          ? null
          : value === "managed"
            ? { mode: "managed", model: CHECKPOINT, consent: false }
            : {
                mode: value as "byok" | "server",
                protocol: "chat-json",
                connection:
                  config.connections.find((c) => !c.subscription)?.id ?? "",
                model: "",
                consent: false,
              },
    });
  return (
    <Card>
      <h2>Décideur interchangeable</h2>
      <p>
        Le mode direct fonctionne sans décideur. Un décideur classe la tâche ;
        le modèle répondant rédige la réponse.
      </p>
      <Field label="Mode du décideur">
        <Select
          value={mode}
          onValueChange={setMode}
          options={[
            { value: "none", label: "Aucun · accès direct" },
            { value: "managed", label: "Modèle ouvert géré par OMR" },
            { value: "byok", label: "Clé API · BYOK" },
            { value: "server", label: "Serveur existant · URL, dont Ollama" },
          ]}
        />
      </Field>
      {d && mode !== "managed" && (
        <>
          <p className="muted">
            {mode === "server"
              ? "Ollama : http://127.0.0.1:11434/v1. Le modèle doit déjà être installé ; OMR ne gère pas ce serveur."
              : "La clé de cette connexion reste dans le coffre OS. Aucune session d’abonnement n’est importée."}
          </p>
          <div className="form-grid">
            <Field label="Connexion du décideur">
              <Select
                value={d.connection ?? ""}
                onValueChange={(value) =>
                  change({
                    ...config,
                    decider: { ...d, connection: value },
                  })
                }
                options={[
                  { value: "", label: "Choisir une connexion" },
                  ...config.connections
                    .filter((c) => !c.subscription)
                    .map((c) => ({
                      value: c.id,
                      label: `${c.name} · ${c.url}`,
                    })),
                ]}
              />
            </Field>
            <Field label="Protocole du décideur">
              <Select
                value={d.protocol ?? "chat-json"}
                onValueChange={(value) =>
                  change({
                    ...config,
                    decider: {
                      ...d,
                      protocol: value as
                        "chat-json" | "jev" | "imajev" | "ollama-systemone",
                      model: value === "jev" ? "jev-1.13.0" : "",
                    },
                  })
                }
                options={[
                  {
                    value: "chat-json",
                    label: "Chat Completions · JSON via pi-ai",
                  },
                  { value: "jev", label: "Jev · SystemOne (décodeur natif)" },
                  { value: "ollama-systemone", label: "Ollama · SystemOne" },
                  {
                    value: "imajev",
                    label: "Imajev · SystemOne (serveur spécialisé)",
                  },
                ]}
              />
            </Field>
            <Field label="Identifiant exact du modèle de décision">
              <Input
                value={d.model}
                onChange={(e) =>
                  change({
                    ...config,
                    decider: { ...d, model: e.target.value },
                  })
                }
              />
            </Field>
          </div>
          <p>
            Destination :{" "}
            <code>
              {deciderTarget(config) && "url" in deciderTarget(config)!
                ? (deciderTarget(config) as { url: string }).url
                : "connexion à choisir"}
            </code>{" "}
            · modèle <code>{d.model || "non renseigné"}</code>
          </p>
          {d.protocol === "jev" && (
            <p className="muted">
              SystemOne /systemone, pas Chat Completions. Jev mappe « direct » à
              1 et « reasoning » à 3. URL habituelle :
              https://api.typesafe.ai/v1.
            </p>
          )}
        </>
      )}
      {d?.protocol === "imajev" && (
        <p className="muted">
          Le serveur Imajev doit charger son véritable décodeur de décisions,
          pas une API chat Ollama. OMR utilise /systemone et refuse les
          abstentions ou une probabilité « unknown » supérieure à 0,25. Les
          poids Imajev ne sont pas gérés ni qualifiés ici.
        </p>
      )}
      {d?.protocol === "ollama-systemone" && (
        <p className="muted">
          Pour un modèle de décision natif Ollama, comme d3:4b. OMR utilise
          /systemone ; une abstention ou une réponse invalide refuse le routage.
        </p>
      )}
      {d && mode === "managed" && (
        <>
          <Badge tone={managed?.running ? "good" : "warn"}>
            {managedNames[managed?.status ?? "absent"] ?? "État inconnu"}
          </Badge>
          <p>
            <b>s1d1 ONNX INT8</b> · révision dac13b5 · CPU. Téléchargement
            public depuis Hugging Face ; aucun prompt envoyé. Six fichiers
            vérifiés par SHA-256, installation atomique, poids sur cet appareil.
          </p>
          <p className="muted">
            Dernier message utilisateur textuel, 1024 tokens maximum. Seuils
            expérimentaux de complexité, pas une mesure de qualité garantie.
            Aucun démarrage automatique. Arrêter interrompt les décisions
            locales en cours.
            {!managed?.supported &&
              " Le mode géré est indisponible sur cet appareil."}
          </p>
          <p aria-live="polite">
            {managed?.downloaded_bytes
              ? `${managed.downloaded_bytes} octets reçus`
              : ""}
            {managed?.error ? ` · ${errorMessage(managed.error)}` : ""}
          </p>
          <Switch
            label="J’autorise le téléchargement des poids publics s1d1 sur cet appareil"
            checked={downloadConsent}
            onCheckedChange={setDownloadConsent}
          />
          <div className="actions">
            <Button
              disabled={
                busy ||
                managed?.active ||
                managed?.running ||
                managed?.supported === false ||
                !downloadConsent
              }
              onClick={() => {
                setDownloadConsent(false);
                void act(() =>
                  command({
                    command: "managed",
                    request: { action: "download", consent: true },
                  }),
                );
              }}
            >
              Télécharger et vérifier s1d1
            </Button>
            <Button
              variant="secondary"
              disabled={
                busy ||
                managed?.active ||
                managed?.running ||
                !managed ||
                managed.supported === false ||
                ["absent", "downloading"].includes(managed.status)
              }
              onClick={() =>
                void act(() =>
                  command({ command: "managed", request: { action: "start" } }),
                )
              }
            >
              Démarrer le modèle géré
            </Button>
            <Button
              variant="secondary"
              disabled={busy || (!managed?.active && !managed?.running)}
              onClick={() =>
                void act(() =>
                  command({
                    command: "managed",
                    request: { action: managed?.active ? "cancel" : "stop" },
                  }),
                )
              }
            >
              {managed?.active ? "Annuler" : "Arrêter le modèle géré"}
            </Button>
          </div>
        </>
      )}
      {d && (
        <Switch
          label={
            mode === "managed"
              ? "J’autorise la classification locale par ce checkpoint s1d1"
              : "J’autorise l’envoi de l’extrait de contexte à ce décideur"
          }
          checked={d.consent}
          onCheckedChange={(consent) => {
            change({ ...config, decider: { ...d, consent } });
            grant(consent ? deciderTarget(config) : null);
          }}
        />
      )}
      <p className="muted">
        Enregistrer ne lance aucun test. Le test envoie la question publique «
        What is the capital of France? » au décideur sélectionné.
      </p>
      <Button
        variant="secondary"
        disabled={
          busy ||
          !config.decider?.consent ||
          (config.decider.mode === "managed" && !managed?.running)
        }
        onClick={() =>
          void act(
            () => command({ command: "test_decision", consent: true }),
            "Décision vérifiée. Consultez le reçu dans l’inspecteur.",
          )
        }
      >
        Tester le décideur · coût API possible
      </Button>
    </Card>
  );
}

export function Onboarding({
  config,
  state,
  busy,
  change,
  grant,
  persist,
  act,
  close,
}: {
  config: Config;
  state: Snapshot;
  busy: boolean;
  change: (value: Config) => void;
  grant: (target: Grant) => void;
  persist: Persist;
  close: () => void;
  act: <T>(
    action: () => Promise<T>,
    success?: string,
  ) => Promise<T | undefined>;
}) {
  const [step, setStep] = useState(
    () => readOnboarding()?.step ?? initialStep(config),
  );
  useEffect(() => {
    writeOnboarding(true, step);
  }, [step]);
  const [name, setName] = useState("Mon serveur");
  const [url, setUrl] = useState("http://127.0.0.1:11434/v1");
  const [model, setModel] = useState("");
  const [secret, setSecret] = useState("");
  const [quality, setQuality] = useState(3);
  const [connectionId, setConnectionId] = useState("");
  const [localError, setLocalError] = useState("");
  useErrorToast(localError);
  async function addConnection(respondent: boolean) {
    const c: Connection = {
      id: connectionId || crypto.randomUUID(),
      name,
      url,
      transport: "pi-ai",
      models: respondent
        ? [
            {
              id: crypto.randomUUID(),
              upstream: model,
              enabled: true,
              protocols: ["responses"],
              tools: false,
              quality,
              input_price: null,
              output_price: null,
              effort: null,
            },
          ]
        : [],
    };
    const next = {
      ...config,
      connections: [
        ...config.connections.filter((item) => item.id !== c.id),
        c,
      ],
    };
    if (!(await persist(next))) return;
    setConnectionId(c.id);
    if (secret) {
      const value = secret;
      setSecret("");
      const saved = await act(async () => {
        await saveSecret(c.id, value);
        return true;
      }, "Clé enregistrée dans le coffre OS.");
      if (!saved) {
        setLocalError(
          "Connexion enregistrée. Renseignez à nouveau la clé pour réessayer le coffre OS.",
        );
        return;
      }
    }
    setLocalError("");
    setConnectionId("");
    setModel("");
    if (respondent) setStep(1);
  }
  const titles = [
    "Modèles répondants",
    "Décideur",
    "Routage",
    "Test explicite",
  ];
  return (
    <section aria-label="Premier démarrage" className="stack">
      <Card>
        <div className="section-heading">
          <div>
            <span className="eyebrow">PREMIER DÉMARRAGE</span>
            <h2>Brancher OMR, à votre rythme</h2>
          </div>
          <Button variant="ghost" onClick={close}>
            Continuer en accès direct
          </Button>
        </div>
        <p>
          Les réglages enregistrés sont conservés. Aucun appel, téléchargement
          ou test ne démarre à votre place.
        </p>
        <nav aria-label="Étapes de configuration" className="actions">
          {titles.map((title, index) => (
            <Button
              key={title}
              variant={step === index ? "default" : "secondary"}
              onClick={() => setStep(index)}
              aria-current={step === index ? "step" : undefined}
            >
              {index + 1}. {title}
            </Button>
          ))}
        </nav>
      </Card>
      {(step === 0 || step === 1) && (
        <Card>
          <h2>
            {step === 0
              ? "Connecter un modèle répondant"
              : "Ajouter une connexion pour le décideur"}
          </h2>
          <p>
            {step === 0
              ? "Responses est le contrat de génération. Indiquez un modèle réellement servi par cet endpoint. Les prix restent inconnus tant qu’ils ne sont pas déclarés."
              : "BYOK et serveur existant utilisent une connexion dédiée ou un fournisseur déjà configuré. Le mode géré n’en a pas besoin."}
          </p>
          <div className="form-grid">
            <Field label="Nom de la connexion guidée">
              <Input
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setConnectionId("");
                }}
              />
            </Field>
            <Field label="URL API du parcours guidé">
              <Input
                value={url}
                onChange={(e) => {
                  setUrl(e.target.value);
                  setConnectionId("");
                }}
              />
            </Field>
            {step === 0 && (
              <>
                <Field label="Modèle répondant · identifiant exact">
                  <Input
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                  />
                </Field>
                <Field label="Qualité déclarée du répondant">
                  <Select
                    value={String(quality)}
                    onValueChange={(value) => setQuality(Number(value))}
                    options={[
                      { value: "1", label: "1 · léger" },
                      { value: "2", label: "2 · intermédiaire" },
                      { value: "3", label: "3 · exigeant" },
                    ]}
                  />
                </Field>
              </>
            )}
            <Field label="Clé API guidée · facultative pour un serveur sans clé">
              <Input
                type="password"
                autoComplete="off"
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
              />
            </Field>
          </div>
          {url.trim().toLowerCase().startsWith("http://") && (
            <p className="muted">
              HTTP ne chiffre ni les requêtes ni la clé API. Utilisez HTTPS sur
              un réseau non fiable.
            </p>
          )}
          {localError && <p role="alert">{localError}</p>}
          <Button
            disabled={
              busy ||
              !name.trim() ||
              !url.trim() ||
              (step === 0 && !model.trim())
            }
            onClick={() => void addConnection(step === 0)}
          >
            {step === 0
              ? "Enregistrer le répondant"
              : "Enregistrer la connexion du décideur"}
          </Button>
          <ul>
            {state.config.connections.flatMap((c) =>
              c.models
                .filter((m) => m.enabled)
                .map((m) => (
                  <li key={m.id}>
                    {c.name} · {m.upstream} · qualité {m.quality}
                  </li>
                )),
            )}
          </ul>
        </Card>
      )}
      {step === 1 && (
        <>
          <DeciderPanel
            config={config}
            state={state}
            busy={busy}
            change={change}
            grant={grant}
            act={act}
          />
          <Button
            disabled={busy}
            onClick={async () => {
              if (await persist(config)) setStep(2);
            }}
          >
            Enregistrer le décideur et continuer
          </Button>
        </>
      )}
      {step === 0 && (
        <Button
          variant="secondary"
          disabled={needsOnboarding(state.config)}
          onClick={() => setStep(1)}
        >
          Continuer avec les répondants enregistrés
        </Button>
      )}
      {step === 2 && (
        <Card>
          <h2>Régler le routage</h2>
          <Switch
            label="Réévaluer à chaque nouveau tour utilisateur"
            checked={config.reevaluate}
            onCheckedChange={(reevaluate) => change({ ...config, reevaluate })}
          />
          <Field label="Contexte du décideur · tokens estimés">
            <Input
              type="number"
              value={config.context_tokens}
              onChange={(e) =>
                change({ ...config, context_tokens: Number(e.target.value) })
              }
            />
          </Field>
          <p>
            Économie, Équilibré et Qualité respectent un plancher de qualité.
            Sans décideur consenti, utilisez une route directe. Les cycles
            d’outils restent attachés au répondant.
          </p>
          <Button
            disabled={busy}
            onClick={async () => {
              if (await persist(config)) setStep(3);
            }}
          >
            Enregistrer le routage
          </Button>
        </Card>
      )}
      {step === 3 && (
        <Card>
          <h2>Lancer un test, explicitement</h2>
          <p>
            Chaque clic ci-dessous envoie une requête. Une API distante peut la
            facturer. Aucun test n’est exécuté à l’ouverture de cette étape.
          </p>
          {config.connections.flatMap((c) =>
            c.models
              .filter((m) => m.enabled)
              .map((m) => (
                <div className="actions" key={m.id}>
                  <code>{m.upstream}</code>
                  <Button
                    disabled={busy}
                    onClick={() =>
                      void act(
                        () =>
                          command({
                            command: "test_generation",
                            model: `direct/${c.id}/${m.id}`,
                            consent: true,
                          }),
                        "Génération vérifiée.",
                      )
                    }
                  >
                    Tester
                  </Button>
                </div>
              )),
          )}
          <Button
            disabled={
              busy ||
              !config.decider?.consent ||
              (config.decider.mode === "managed" && !state.managed?.running)
            }
            onClick={() =>
              void act(
                () => command({ command: "test_decision", consent: true }),
                "Décision vérifiée.",
              )
            }
          >
            Tester la décision · coût API possible
          </Button>
          <p>Les reçus restent dans l’inspecteur, sans contenu des messages.</p>
          <Button variant="secondary" onClick={close}>
            Revenir à l’état du routeur
          </Button>
        </Card>
      )}
    </section>
  );
}
