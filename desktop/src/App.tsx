import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import { enable, disable, isEnabled } from "@tauri-apps/plugin-autostart";
import {
  Activity,
  ArrowDownToLine,
  ArrowRight,
  CircleDot,
  Gauge,
  GitBranch,
  Layers,
  Plus,
  MessageSquare,
  RefreshCw,
  Search,
  Settings2,
  ShieldCheck,
  Unplug,
  X,
  Zap,
} from "lucide-react";
import {
  Badge,
  Button,
  Card,
  Field,
  Input,
  Modal,
  Select,
  Switch,
} from "./components/ui";
import { version } from "../package.json";
import { command, errorMessage, saveSecret } from "./api";
import { useErrorToast, useNotify } from "./notifications";
import { NativeStrategies } from "./components/native-strategies";
import { ChatPlayground } from "./chat-playground";
import { SetupTour, readTour, saveTour } from "./setup-tour";
import { SubscriptionAccess } from "./subscription-access";
import { ProviderSetup, ConfigFilePanel } from "./provider-setup";
import { ConfigAutosave, type SaveStatus, type Grant } from "./config-autosave";
import { ModelCatalogue, newModel } from "./components/model-catalogue";
import { ModelRanking } from "./components/model-ranking";
import { chooseQuality } from "./benchmark-ranking";
import {
  Onboarding,
  DeciderPanel,
  deciderTarget,
  needsOnboarding,
  writeOnboarding,
} from "./components/onboarding";
import {
  Topology,
  ReceiptDetails,
  profileNames,
  statusNames,
} from "./components/observability";
import type { Config, Connection, Model, Receipt, Snapshot } from "./types";
import {
  comparisonTotals,
  money,
  number,
  routeStats,
  usageTotals,
} from "./metrics";

const pages = [
  "État",
  "Fournisseurs",
  "Profils & règles",
  "Stratégies natives",
  "Chat",
  "Consommation",
  "Inspecteur",
  "Réglages",
] as const;
type Page = (typeof pages)[number];
const everydayPages: Page[] = ["État", "Fournisseurs", "Chat", "Réglages"];
const pageIcons = [
  Activity,
  Unplug,
  GitBranch,
  Layers,
  MessageSquare,
  Gauge,
  Search,
  Settings2,
];
const descriptions: Record<Page, string> = {
  État: "Le routage, sur votre appareil.",
  Fournisseurs: "Vos connexions. Vos modèles.",
  "Profils & règles": "Une politique pour chaque intention.",
  "Stratégies natives": "Des commandes explicites, dans une session isolée.",
  Chat: "Choisissez un profil automatique ou un modèle direct.",
  Consommation: "Mesurer ce qui a réellement circulé.",
  Inspecteur: "Comprendre chaque requête.",
  Réglages: "Votre environnement de travail.",
};
const clone = <T,>(value: T): T => structuredClone(value);
const directId = (c: Connection, m: Model) => `direct/${c.id}/${m.id}`;

function Stat({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <Card className="stat">
      <span className="eyebrow">{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </Card>
  );
}

export default function App() {
  const notify = useNotify();
  const [page, setPage] = useState<Page>("État");
  const [onboarding, setOnboarding] = useState<boolean>();
  const [tour, setTour] = useState<number | null>(null);
  const [state, setState] = useState<Snapshot>();
  const [draft, setDraft] = useState<Config>();
  const [baseRevision, setBaseRevision] = useState(0);
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("saved");
  const [saveError, setSaveError] = useState("");
  const [healthy, setHealthy] = useState(false);
  const [error, setError] = useState("");
  useErrorToast(!healthy ? error : undefined);
  useErrorToast(saveError !== error ? saveError : undefined);
  useErrorToast(
    state?.receipt_storage === "unavailable"
      ? "Le stockage des reçus est indisponible. Les mesures restent en mémoire et peuvent être perdues à la fermeture. Vérifiez l’espace et les droits du dossier de l’application."
      : "",
  );
  const [busy, setBusy] = useState(false);
  const [reloading, setReloading] = useState(false);
  const reloadLock = useRef(false);
  const [credentials, setCredentials] = useState<{
    endpoint: string;
    key: string;
  }>();
  const [quitting, setQuitting] = useState(false);
  const [force, setForce] = useState(false);
  const consentFor = useRef<Grant>(null);
  const draftRef = useRef<Config | null>(null);
  const [autosave] = useState(
    () =>
      new ConfigAutosave(
        (config, revision, grant) =>
          command<Snapshot>({
            command: "save_config",
            config,
            revision,
            consent_for: grant,
          }),
        (snapshot, current) => {
          setState(snapshot);
          setBaseRevision(snapshot.revision);
          if (current) {
            draftRef.current = clone(snapshot.config);
            setDraft(draftRef.current);
            setDirty(false);
            consentFor.current = null;
          }
        },
        (status, error) => {
          setSaveStatus(status);
          setSaveError(status === "error" ? errorMessage(error) : "");
        },
      ),
  );
  function setConsentFor(grant: Grant) {
    consentFor.current = grant;
    if (draftRef.current) autosave.edit(draftRef.current, grant);
  }
  const setQuitOpen = useCallback((open: boolean) => {
    setForce(false);
    setQuitting(open);
  }, []);
  const [autostart, setAutostart] = useState<boolean>();
  const [theme, setTheme] = useState("system");
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  const refresh = useCallback(async () => {
    try {
      const snapshot = await command<Snapshot>({ command: "snapshot" });
      setState(snapshot);
      setHealthy(true);
      return snapshot;
    } catch (e) {
      setHealthy(false);
      setError(errorMessage(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
    const id = setInterval(() => void refresh(), 4000);
    return () => clearInterval(id);
  }, [refresh]);
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [page]);
  useEffect(() => {
    if (state && !draft) {
      autosave.reset(state);
      draftRef.current = clone(state.config);
      setDraft(clone(state.config));
      setBaseRevision(state.revision);
      const progress = readTour();
      setOnboarding(false);
      if (progress?.open || (!progress && needsOnboarding(state.config)))
        setTour(progress?.step ?? 0);
    }
  }, [state, draft]);
  useEffect(() => () => autosave.dispose(), [autosave]);
  useEffect(() => {
    const unlisten = listen("quit-requested", () => setQuitOpen(true)).catch(
      () => () => {},
    );
    const navigation = listen<string>("navigate", (event) => {
      if (pages.includes(event.payload as Page)) setPage(event.payload as Page);
    }).catch(() => () => {});
    void isEnabled()
      .then(setAutostart)
      .catch(() => setAutostart(undefined));
    return () => {
      void unlisten.then((fn) => fn());
      void navigation.then((fn) => fn());
    };
  }, []);
  function edit(next: Config) {
    if (reloadLock.current) return;
    if (
      JSON.stringify(deciderTarget(draftRef.current ?? undefined)) !==
      JSON.stringify(deciderTarget(next))
    ) {
      consentFor.current = null;
      if (next.decider)
        next = { ...next, decider: { ...next.decider, consent: false } };
    }
    draftRef.current = next;
    setDraft(next);
    setDirty(true);
    autosave.edit(next, consentFor.current);
  }
  async function act<T>(
    action: () => Promise<T>,
    success?: string,
  ): Promise<T | undefined> {
    setBusy(true);
    setError("");
    try {
      const result = await autosave.run(action);
      await refresh();
      if (success) notify(success);
      return result;
    } catch (e) {
      const message = errorMessage(e);
      setError(message);
      notify(message, "error");
      await refresh();
    } finally {
      setBusy(false);
    }
  }
  async function save(config = draftRef.current, grant = consentFor.current) {
    if (!config) return false;
    draftRef.current = config;
    setDraft(config);
    setDirty(true);
    autosave.edit(config, grant);
    return Boolean(await act(async () => true));
  }
  const reload = async () => {
    if (reloadLock.current) return;
    reloadLock.current = true;
    setReloading(true);
    setBusy(true);
    try {
      const accepted = await autosave.discard();
      const latest = (await refresh()) ?? accepted;
      if (!latest) return;
      autosave.reset(latest);
      consentFor.current = null;
      draftRef.current = clone(latest.config);
      setDraft(draftRef.current);
      setBaseRevision(latest.revision);
      setDirty(false);
      notify("Brouillon abandonné.");
    } finally {
      reloadLock.current = false;
      setReloading(false);
      setBusy(false);
    }
  };
  const models =
    state?.config.connections.flatMap((c) => c.models.map((m) => ({ c, m }))) ??
    [];
  const receipts = state?.receipts ?? [];
  async function loadConfigFile() {
    if (dirty || reloadLock.current) return;
    reloadLock.current = true;
    setReloading(true);
    try {
      await act(async () => {
        const next = await command<Snapshot>({
          command: "save_config",
          source: "file",
          revision: baseRevision,
        });
        setState(next);
        autosave.reset(next);
        draftRef.current = clone(next.config);
        setDraft(structuredClone(next.config));
        setBaseRevision(next.revision);
        consentFor.current = null;
        notify(
          "Fichier chargé. Les prochaines requêtes utilisent ces réglages.",
        );
      });
    } finally {
      reloadLock.current = false;
      setReloading(false);
    }
  }
  const changeConnection = (connection: Connection) => {
    if (draft)
      edit({
        ...draft,
        connections: draft.connections.map((c) =>
          c.id === connection.id ? connection : c,
        ),
        baseline:
          draft.baseline &&
          draft.connections
            .find((c) => c.id === connection.id)
            ?.models.some((m) => m.id === draft.baseline) &&
          !connection.models.some((m) => m.id === draft.baseline)
            ? null
            : draft.baseline,
      });
  };
  const suggestedBaseline = Object.entries(
    state?.summary.direct_frequencies_30d ?? {},
  )
    .filter(([id]) => models.some(({ m }) => m.id === id && m.enabled))
    .sort((a, b) => b[1] - a[1])[0]?.[0];
  const [selected, setSelected] = useState<Receipt>();
  const [period, setPeriod] = useState(30);
  const [mode, setMode] = useState("all");
  const filtered = receipts.filter(
    (r) =>
      r.timestamp * 1000 >= Date.now() - period * 86400000 &&
      (mode === "all" ||
        (mode === "direct" || mode === "native"
          ? r.mode === mode
          : r.profile === mode)),
  );
  const totals = usageTotals(filtered.filter((r) => r.mode !== "native"));
  const comparisons = comparisonTotals(filtered);
  function navigationItem(name: Page) {
    const Icon = pageIcons[pages.indexOf(name)];
    return (
      <button
        key={name}
        className={page === name ? "nav active" : "nav"}
        aria-current={page === name ? "page" : undefined}
        onClick={() => setPage(name)}
      >
        <Icon size={18} />
        {name}
        {name === "Inspecteur" && receipts.length > 0 && (
          <span className="nav-count">{receipts.length}</span>
        )}
      </button>
    );
  }
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <img
            className="brand-icon"
            src="/brand/app-128.png"
            alt=""
            width="40"
            height="40"
          />
          <div>
            <b>Open Model Router</b>
            <small>ESPACE LOCAL</small>
          </div>
        </div>
        <nav aria-label="Navigation principale">
          {everydayPages.map(navigationItem)}
          <details
            className="nav-advanced"
            open={!everydayPages.includes(page)}
          >
            <summary>Avancé</summary>
            {pages
              .filter((name) => !everydayPages.includes(name))
              .map(navigationItem)}
          </details>
        </nav>
        <div className="sidebar-bottom">
          <Badge tone={healthy ? "good" : "warn"}>
            <CircleDot size={11} />
            {healthy ? "Moteur disponible" : "Moteur indisponible"}
          </Badge>
          <p>
            Clés fournisseurs : coffre OS.
            <br />
            Vos reçus restent sur cet appareil.
          </p>
          <Button variant="ghost" onClick={() => setQuitOpen(true)}>
            Quitter OMR Desktop…
          </Button>
          {reloading && <p role="status">Rechargement de la configuration…</p>}
        </div>
      </aside>
      <main inert={reloading} aria-busy={reloading}>
        <header>
          <div className="breadcrumb" aria-label="Fil de navigation">
            <span>Espace local</span>
            <span aria-hidden="true">/</span>
            <strong>{page}</strong>
          </div>
          <div className="header-actions">
            {draft && saveStatus === "saved" && !dirty && (
              <span className="save-state" role="status">
                <ShieldCheck size={14} />
                Réglages enregistrés
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setPage("État");
                writeOnboarding(true);
                setOnboarding(true);
              }}
            >
              Reprendre la configuration
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                saveTour(true, 0);
                setOnboarding(false);
                setTour(0);
              }}
            >
              Visite guidée
            </Button>
            <Badge>{`v${version}`}</Badge>
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => void refresh()}
              aria-label="Actualiser"
            >
              <RefreshCw size={16} />
            </Button>
          </div>
        </header>
        {tour !== null && state && (
          <SetupTour
            initialStep={tour}
            navigate={setPage}
            close={() => setTour(null)}
          />
        )}
        <div className="page-intro">
          <span className="eyebrow">
            {page === "État" ? "ESPACE DE ROUTAGE" : "OPEN MODEL ROUTER"}
          </span>
          <h1>{page === "État" ? "Votre routage, en un regard." : page}</h1>
          <p className="page-description">{descriptions[page]}</p>
        </div>

        {draft && (
          <ModelRanking
            config={draft}
            change={edit}
            visible={page === "Fournisseurs"}
            run={act}
          />
        )}
        {state?.receipt_storage === "unavailable" && (
          <div className="alert error" role="alert">
            Le stockage des reçus est indisponible. Les mesures restent en
            mémoire et peuvent être perdues à la fermeture. Vérifiez l’espace et
            les droits du dossier de l’application.
          </div>
        )}

        {draft && (saveStatus !== "saved" || dirty) && (
          <div className="save-bar" data-state={saveStatus}>
            <span role="status" aria-live="polite">
              {
                {
                  saved: "Réglages enregistrés",
                  pending: "Enregistrement en attente…",
                  saving: "Enregistrement…",
                  error: "Réglages non enregistrés",
                }[saveStatus]
              }
              {dirty && state?.revision !== baseRevision
                ? " · une autre révision existe"
                : ""}
            </span>
            {saveError && <span role="alert">{saveError}</span>}
            {dirty && (
              <Button
                variant="ghost"
                disabled={busy}
                onClick={() => void reload()}
              >
                Abandonner le brouillon
              </Button>
            )}
            {saveError && (
              <Button disabled={busy || !healthy} onClick={() => void save()}>
                Réessayer l’enregistrement
              </Button>
            )}
          </div>
        )}
        {!state || !draft ? (
          <Card className="empty" role="status" aria-busy={!error}>
            <Unplug size={32} />
            <h2>
              {error
                ? "Connexion au moteur impossible"
                : "Connexion au moteur…"}
            </h2>
            <p>Le paquet embarque son moteur. Aucun Python à installer.</p>
            <Button onClick={() => void refresh()}>Réessayer</Button>
          </Card>
        ) : (
          <>
            {page === "État" && onboarding && (
              <Onboarding
                config={draft}
                state={state}
                busy={busy}
                change={edit}
                grant={setConsentFor}
                persist={save}
                act={act}
                close={() => {
                  writeOnboarding(false);
                  setOnboarding(false);
                }}
              />
            )}
            {page === "État" && (
              <>
                <div className="overview-heading">
                  <div className="service-strip" aria-label="État du service">
                    <span
                      className={
                        healthy ? "service-state" : "service-state unavailable"
                      }
                    >
                      <CircleDot size={15} />
                      {healthy ? "Moteur disponible" : "Moteur indisponible"}
                    </span>
                    <span>
                      {state.config.connections.length} fournisseur
                      {state.config.connections.length > 1 ? "s" : ""}
                    </span>
                    <span>
                      {models.filter(({ m }) => m.enabled).length} modèle
                      {models.filter(({ m }) => m.enabled).length > 1
                        ? "s"
                        : ""}
                    </span>
                    <span title="Fermer la fenêtre n’arrête pas les requêtes">
                      {state.active} en cours
                    </span>
                  </div>
                  <div className="overview-actions">
                    <Button onClick={() => setPage("Chat")}>
                      <MessageSquare size={15} />
                      Ouvrir le Chat
                      <ArrowRight size={14} />
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => setPage("Fournisseurs")}
                    >
                      <Plus size={15} />
                      Ajouter un fournisseur
                    </Button>
                  </div>
                </div>
                <Topology
                  config={state.config}
                  receipts={receipts}
                  revision={state.revision}
                />
                <div className="columns overview-panels">
                  <Card>
                    <div className="section-heading">
                      <h2>Activité récente</h2>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setPage("Inspecteur")}
                      >
                        Tout voir <ArrowRight size={14} />
                      </Button>
                    </div>
                    {!receipts.length ? (
                      <div className="empty compact">
                        <Activity size={25} />
                        <h3>Aucune requête observée</h3>
                        <p>
                          Essayez un modèle dans le Chat. Les reçus apparaîtront
                          ici, sans enregistrer le contenu de vos échanges.
                        </p>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setPage("Chat")}
                        >
                          Ouvrir le Chat
                          <ArrowRight size={14} />
                        </Button>
                      </div>
                    ) : (
                      receipts
                        .slice(-4)
                        .reverse()
                        .map((row) => (
                          <button
                            className="receipt"
                            key={row.request_id}
                            onClick={(event) => {
                              event.currentTarget.focus();
                              setSelected(row);
                            }}
                          >
                            <span
                              className={`receipt-dot ${row.status === "completed" ? "ok" : ""}`}
                            />
                            <span>
                              <b>
                                {row.native ? `${row.native.action} · ` : ""}
                                {row.model_requested ||
                                  "Route non sélectionnée"}
                              </b>
                              <small>
                                {row.mode === "direct"
                                  ? "Direct"
                                  : profileNames[row.profile || ""] ||
                                    "Automatique"}{" "}
                                · {statusNames[row.status] || row.status}
                              </small>
                            </span>
                            <ArrowRight size={14} />
                          </button>
                        ))
                    )}
                  </Card>
                  <Card>
                    <div className="section-heading">
                      <h2>Connexions</h2>
                      <Badge>{state.config.connections.length}</Badge>
                    </div>
                    <div className="connection-list">
                      {state.config.connections.length ? (
                        state.config.connections.map((connection) => (
                          <div
                            className="connection-summary"
                            key={connection.id}
                          >
                            <span className="connection-icon">
                              <Unplug size={17} />
                            </span>
                            <div>
                              <strong>{connection.name}</strong>
                              <small>
                                {
                                  connection.models.filter(
                                    (model) => model.enabled,
                                  ).length
                                }{" "}
                                modèle(s) autorisé(s)
                              </small>
                            </div>
                            <Badge>Configuré</Badge>
                          </div>
                        ))
                      ) : (
                        <p>
                          Aucun fournisseur. Ajoutez votre serveur local ou
                          votre API pour commencer.
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setPage("Fournisseurs")}
                    >
                      Gérer les fournisseurs <ArrowRight size={14} />
                    </Button>
                  </Card>
                </div>
                <details className="client-access card" data-tour="client">
                  <summary>
                    Brancher un client API<span>URL locale et clé d’accès</span>
                  </summary>
                  <div className="columns">
                    <Card>
                      <div className="section-heading">
                        <h2>Accès sur cet appareil</h2>
                        <ShieldCheck size={18} />
                      </div>
                      <p>
                        Chat Completions, Responses ou Messages. Accès limité à
                        cet appareil.
                      </p>
                      <Field label="URL de base">
                        <Input
                          readOnly
                          value={`http://127.0.0.1:${state.port}/v1`}
                        />
                      </Field>
                      <p className="muted">
                        La clé et le port changent au redémarrage. Ne partagez
                        pas la clé.
                      </p>
                      <Button
                        variant="secondary"
                        disabled={busy}
                        onClick={() =>
                          void act(async () => {
                            const value = await command<{
                              endpoint: string;
                              key: string;
                            }>({ command: "credentials" });
                            setCredentials(value);
                          })
                        }
                      >
                        Afficher la clé locale
                      </Button>
                      {credentials && (
                        <Field label="Clé API locale — sélectionnez pour copier">
                          <Input
                            readOnly
                            autoComplete="off"
                            value={credentials.key}
                            onFocus={(e) => e.currentTarget.select()}
                          />
                          <Button
                            variant="ghost"
                            onClick={() => setCredentials(undefined)}
                          >
                            Masquer
                          </Button>
                        </Field>
                      )}
                      <p className="muted">
                        Continuité : envoyez X-OMR-Session avec un UUID par
                        conversation. Sans cet en-tête, chaque requête est
                        indépendante.
                      </p>
                    </Card>
                    <Card>
                      <h2>Politique active</h2>
                      <dl>
                        <dt>Réévaluation</dt>
                        <dd>
                          {state.config.reevaluate
                            ? "À chaque tour utilisateur"
                            : "Choix conservé par session"}
                        </dd>
                        <dt>Budget de contexte estimé</dt>
                        <dd>{number(state.config.context_tokens)} tokens</dd>
                        <dt>Décideur</dt>
                        <dd>
                          {state.config.decider?.consent
                            ? "Contexte consenti"
                            : "Non configuré · profils bloqués"}
                        </dd>
                      </dl>
                      <Button
                        variant="secondary"
                        onClick={() => setPage("Profils & règles")}
                      >
                        Modifier les règles <ArrowRight size={16} />
                      </Button>
                    </Card>
                  </div>
                </details>
              </>
            )}
            {page === "Chat" && (
              <ChatPlayground config={state.config} revision={state.revision} />
            )}
            {page === "Réglages" && (
              <>
                <Card>
                  <h2>Apparence</h2>
                  <p>
                    Le thème système suit les préférences de votre appareil.
                  </p>
                  <Field label="Thème de l’interface">
                    <Select
                      value={theme}
                      onValueChange={setTheme}
                      options={[
                        { value: "system", label: "Système" },
                        { value: "dark", label: "Sombre" },
                        { value: "light", label: "Clair" },
                      ]}
                    />
                  </Field>
                  <small>
                    Le choix manuel reste actif jusqu’au prochain lancement.
                  </small>
                </Card>
                <Card>
                  <h2>Fonctionnement en arrière-plan</h2>
                  <p>
                    Sous Linux, fermer minimise la fenêtre. Sur macOS/Windows,
                    elle est masquée si l’icône système est disponible ; sinon,
                    l’arrêt est proposé avec confirmation.
                  </p>
                  <Switch
                    label="Lancer OMR à l’ouverture de session"
                    checked={autostart ?? false}
                    disabled={busy || autostart === undefined}
                    onCheckedChange={(value) =>
                      void act(async () => {
                        await (value ? enable() : disable());
                        setAutostart(await isEnabled());
                      })
                    }
                  />
                  {autostart === undefined && (
                    <p className="muted">Autostart non vérifié sur cet hôte.</p>
                  )}
                  <hr />
                  <h3>Intégrations natives</h3>
                  <p className="muted">
                    Les sessions Hermes, Codex, Claude Code et OMP ne sont pas
                    importées. Utilisez un endpoint API compatible ; une
                    souscription native n’est pas une clé API portable.
                  </p>
                  <Badge tone="warn">
                    Compaction & délégation indisponibles
                  </Badge>
                </Card>
              </>
            )}
            {page === "Fournisseurs" && (
              <>
                <ConfigFilePanel
                  state={state}
                  busy={busy || !healthy}
                  dirty={dirty}
                  load={() => void loadConfigFile()}
                />
                <div data-tour="providers">
                  <ProviderSetup
                    busy={busy}
                    add={(connection) =>
                      edit({
                        ...draft,
                        connections: [...draft.connections, connection],
                        decider:
                          !draft.decider &&
                          connection.url === "https://api.typesafe.ai/v1"
                            ? {
                                connection: connection.id,
                                model: "jev-1.13.0",
                                mode: "byok",
                                protocol: "jev",
                                consent: false,
                              }
                            : draft.decider,
                      })
                    }
                  />
                </div>
                {!draft.connections.length && (
                  <Card className="empty">
                    <Unplug size={32} />
                    <h2>Aucun fournisseur configuré</h2>
                    <p>
                      Ajoutez votre endpoint API et ses modèles. Aucune clé
                      n’est importée automatiquement.
                    </p>
                  </Card>
                )}
                {draft.connections.map((c) => (
                  <ConnectionCard
                    key={c.id}
                    connection={c}
                    state={state}
                    busy={busy}
                    change={changeConnection}
                    remove={() =>
                      edit({
                        ...draft,
                        connections: draft.connections.filter(
                          (value) => value.id !== c.id,
                        ),
                        decider:
                          draft.decider?.connection === c.id
                            ? null
                            : draft.decider,
                        baseline: c.models.some((m) => m.id === draft.baseline)
                          ? null
                          : draft.baseline,
                      })
                    }
                    act={act}
                  />
                ))}
              </>
            )}
            {page === "Profils & règles" && (
              <>
                <p className="intro">
                  Le décideur classe la tâche. Votre politique choisit parmi les
                  modèles compatibles et autorisés.
                </p>
                <div className="profiles" data-tour="profiles">
                  {Object.entries(profileNames).map(([id, title], i) => (
                    <Card key={id}>
                      <span className="profile-icon">
                        {i === 0 ? (
                          <Zap size={20} />
                        ) : i === 1 ? (
                          <Layers size={20} />
                        ) : (
                          <ShieldCheck size={20} />
                        )}
                      </span>
                      <h2>{title}</h2>
                      <code>omr/{id}</code>
                      <p>
                        {
                          [
                            "Coût déclaré minimal respectant l’exigence de la tâche.",
                            "Plancher de qualité déclaré 2, puis coût minimal.",
                            "Plancher de qualité déclaré 3, puis coût minimal.",
                          ][i]
                        }
                      </p>
                      <Badge tone={draft.decider?.consent ? "good" : "warn"}>
                        {draft.decider?.consent
                          ? "Décideur configuré"
                          : "Bloqué sans décideur consenti"}
                      </Badge>
                    </Card>
                  ))}
                </div>
                <div data-tour="decider">
                  <DeciderPanel
                    config={draft}
                    state={state}
                    busy={busy}
                    change={edit}
                    grant={setConsentFor}
                    act={act}
                  />
                </div>
                <Card>
                  <h2>Réévaluation & contexte</h2>
                  <Switch
                    label="Réévaluer à chaque nouveau tour utilisateur"
                    checked={draft.reevaluate}
                    onCheckedChange={(reevaluate) =>
                      edit({ ...draft, reevaluate })
                    }
                  />
                  <p className="muted">
                    Sans réévaluation, le premier choix reste attaché à la
                    session et au profil. Un cycle d’outils ne déclenche pas de
                    switch. Aucun repli silencieux.
                  </p>
                  <div className="form-grid">
                    {(
                      [
                        [
                          "context_tokens",
                          "Extrait conversation · tokens estimés",
                        ],
                        ["total_tokens", "Enveloppe totale · tokens estimés"],
                        [
                          "max_messages",
                          "Messages maximum · vide = sans plafond",
                        ],
                        [
                          "expected_output",
                          "Sortie attendue pour l’estimation",
                        ],
                      ] as const
                    ).map(([key, label]) => (
                      <Field key={key} label={label}>
                        <Input
                          type="number"
                          min={key === "max_messages" ? 1 : 0}
                          value={draft[key] ?? ""}
                          onChange={(e) =>
                            edit({
                              ...draft,
                              [key]:
                                e.target.value === "" && key === "max_messages"
                                  ? null
                                  : Number(e.target.value),
                            })
                          }
                        />
                      </Field>
                    ))}
                    <Field label="Économie minimale avant changement · %">
                      <Input
                        type="number"
                        step="1"
                        min="0"
                        max="100"
                        value={Math.round(draft.switch_margin * 100)}
                        onChange={(e) =>
                          edit({
                            ...draft,
                            switch_margin: Number(e.target.value) / 100,
                          })
                        }
                      />
                    </Field>
                  </div>
                  <p className="muted">
                    Estimateur conservateur : octets UTF-8, pas un tokenizer
                    exact. Les tours et groupes outils restent entiers ; un tour
                    courant trop grand est refusé.
                  </p>
                </Card>
                <Card>
                  <h2>Référence de coût</h2>
                  <p>
                    Coût recalculé au même volume de tokens observés. Ce n’est
                    ni une facture ni une économie de tokens. Sans tarifs, la
                    comparaison reste non mesurée.
                  </p>
                  <Field label="Modèle de référence">
                    <Select
                      value={draft.baseline ?? ""}
                      onValueChange={(value) =>
                        edit({ ...draft, baseline: value || null })
                      }
                      options={[
                        { value: "", label: "Aucune référence" },
                        ...models.map(({ c, m }) => ({
                          value: m.id,
                          label: `${c.name} / ${m.upstream}`,
                        })),
                      ]}
                    />
                  </Field>
                  {suggestedBaseline && !draft.baseline && (
                    <Button
                      variant="secondary"
                      onClick={() =>
                        edit({ ...draft, baseline: suggestedBaseline })
                      }
                    >
                      Utiliser le modèle direct le plus choisi sur 30 jours
                    </Button>
                  )}
                  <h3>Historique personnel · 30 jours</h3>
                  {Object.keys(state.summary.direct_frequencies_30d).length ? (
                    Object.entries(state.summary.direct_frequencies_30d)
                      .sort((a, b) => b[1] - a[1])
                      .map(([id, count]) => (
                        <p key={id}>
                          <code>
                            {models.find(({ m }) => m.id === id)?.m.upstream ??
                              id}
                          </code>{" "}
                          · {count} choix {count > 1 ? "directs" : "direct"}
                        </p>
                      ))
                  ) : (
                    <p className="muted">
                      Aucun historique admissible. Les profils automatiques
                      n’inventent pas vos préférences.
                    </p>
                  )}
                </Card>
                <Card>
                  <h2>Révisions locales</h2>
                  <p>
                    Configuration active : révision {state.revision}. Restaurer
                    applique une nouvelle révision sans redémarrer le moteur. Un
                    nouvel accord est requis pour le décideur après
                    restauration.
                  </p>
                  <div className="revision-list">
                    {state.history
                      .slice()
                      .reverse()
                      .map((item) => (
                        <Button
                          key={item.revision}
                          variant="secondary"
                          disabled={busy || dirty}
                          onClick={() => void save(item.config)}
                        >
                          Restaurer r{item.revision}
                        </Button>
                      ))}
                  </div>
                </Card>
              </>
            )}
            {page === "Stratégies natives" && state.native && (
              <NativeStrategies
                state={state.native}
                run={async (request) => {
                  await command({ command: "native", request });
                  await refresh();
                }}
              />
            )}
            {(page === "Consommation" || page === "Inspecteur") && (
              <div className="filters">
                <label>
                  Période
                  <Select
                    value={String(period)}
                    onValueChange={(value) => setPeriod(Number(value))}
                    options={[
                      { value: "1", label: "24 heures" },
                      { value: "7", label: "7 jours" },
                      { value: "30", label: "30 jours" },
                    ]}
                  />
                </label>
                <label>
                  Route
                  <Select
                    value={mode}
                    onValueChange={setMode}
                    options={[
                      { value: "all", label: "Toutes" },
                      { value: "direct", label: "Direct" },
                      { value: "native", label: "Session native" },
                      ...Object.entries(profileNames).map(([value, label]) => ({
                        value,
                        label,
                      })),
                    ]}
                  />
                </label>
                <Button
                  variant="secondary"
                  disabled={busy}
                  onClick={() =>
                    void act(async () => {
                      const result = await command<{ path: string }>({
                        command: "export_receipts",
                      });
                      notify(`Reçus exportés sans transcript : ${result.path}`);
                    })
                  }
                >
                  <ArrowDownToLine size={16} />
                  Exporter tous les reçus
                </Button>
              </div>
            )}
            {page === "Consommation" && (
              <>
                <div className="stats">
                  <Stat
                    label="TOKENS ENTRÉE OBSERVÉS"
                    value={number(totals.input)}
                    detail={`${totals.unknown} requête(s) partiellement non mesurée(s)`}
                  />
                  <Stat
                    label="TOKENS SORTIE OBSERVÉS"
                    value={number(totals.output)}
                    detail="Raisonnement inclus, si fourni"
                  />
                  <Stat
                    label="ÉCART DE REPRICING · AUTO"
                    value={money(comparisons.difference)}
                    detail={`${comparisons.measured} reçu(s) comparable(s) · hors décideur`}
                  />
                </div>
                <Card>
                  <div className="section-heading">
                    <h2>Détail des catégories</h2>
                    <Badge>Pas une facture</Badge>
                  </div>
                  <div className="category-row">
                    <div>
                      <small>Cache lu · sous-catégorie</small>
                      <strong>{number(totals.cache)}</strong>
                    </div>
                    <div>
                      <small>Raisonnement · sous-catégorie</small>
                      <strong>{number(totals.reasoning)}</strong>
                    </div>
                    <div>
                      <small>Décideur · entrée + sortie séparées</small>
                      <strong>{number(totals.decision)}</strong>
                    </div>
                  </div>
                  <p className="muted">
                    Cache et raisonnement ne sont pas ajoutés aux totaux. Un
                    écart négatif signifie que le modèle choisi est plus cher
                    que la référence. Les tarifs cache inconnus ne sont pas
                    déduits.
                  </p>
                </Card>
                <Card>
                  <h2>Modèles & routes</h2>
                  {!filtered.length ? (
                    <div className="empty">
                      <Gauge size={30} />
                      <h3>Aucune consommation observée</h3>
                      <p>
                        Les appels de vos clients et les tests explicites
                        apparaîtront ici.
                      </p>
                    </div>
                  ) : (
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Modèle demandé / confirmé</th>
                            <th>Mode</th>
                            <th>Appels / erreurs</th>
                            <th>Entrée / sortie</th>
                            <th>Durée moyenne</th>
                          </tr>
                        </thead>
                        <tbody>
                          {routeStats(
                            filtered.filter((r) => r.mode !== "native"),
                          ).map((group) => (
                            <tr key={group.key}>
                              <td>
                                <b>{group.model}</b>
                                <small>{group.confirmed}</small>
                                <small>
                                  {state.config.connections.find(
                                    (c) => c.id === group.rows[0].connection,
                                  )?.name ?? "Connexion inconnue"}
                                </small>
                              </td>
                              <td>{group.mode}</td>
                              <td>
                                {group.calls} / {group.failures}
                              </td>
                              <td>
                                {number(usageTotals(group.rows).input)} /{" "}
                                {number(usageTotals(group.rows).output)}
                              </td>
                              <td>{number(group.duration / group.calls)} ms</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </Card>
              </>
            )}
            {page === "Inspecteur" && (
              <Card data-tour="inspector">
                <div className="section-heading">
                  <h2>Reçus de requêtes</h2>
                  <Badge>{filtered.length} reçu(s)</Badge>
                </div>
                <p className="muted">
                  Identités, décision, usage et erreurs bornées. Aucun prompt ni
                  réponse enregistré.
                </p>
                {!filtered.length ? (
                  <div className="empty">
                    <Search size={30} />
                    <h3>Aucun reçu pour cette période</h3>
                    <p>
                      Choisissez une route directe ou un profil dans votre
                      client API.
                    </p>
                  </div>
                ) : (
                  <div className="receipt-list">
                    {filtered
                      .slice()
                      .reverse()
                      .map((row) => (
                        <button
                          className="receipt"
                          key={row.request_id}
                          onClick={(event) => {
                            event.currentTarget.focus();
                            setSelected(row);
                          }}
                        >
                          <span
                            className={`receipt-dot ${row.status === "completed" ? "ok" : ""}`}
                          />
                          <span>
                            <b>
                              {row.native ? `${row.native.action} · ` : ""}
                              {row.model_requested ?? "Route non sélectionnée"}
                            </b>
                            <small>
                              {new Date(row.timestamp * 1000).toLocaleString(
                                "fr-FR",
                              )}{" "}
                              ·{" "}
                              {row.mode === "direct"
                                ? "Direct"
                                : row.mode === "native"
                                  ? "Session native"
                                  : (row.profile ?? "Automatique")}
                            </small>
                          </span>
                          <Badge
                            tone={row.status === "completed" ? "good" : "warn"}
                          >
                            {statusNames[row.status] || row.status}
                          </Badge>
                          <span>{number(row.elapsed_ms)} ms</span>
                          <ArrowRight size={16} />
                        </button>
                      ))}
                  </div>
                )}
              </Card>
            )}
          </>
        )}
        <footer>
          <span>
            <ShieldCheck size={13} />
            Contrôle local · reçus sans transcript
          </span>
          <span>
            OMR Desktop /{" "}
            {state ? `configuration r${state.revision}` : "moteur non connecté"}
          </span>
        </footer>
      </main>
      <Modal
        open={!!selected}
        onOpenChange={(value) => !value && setSelected(undefined)}
        title="Détail du reçu"
        description="Métadonnées locales uniquement. Aucun lien de conversation natif disponible."
      >
        {selected && <ReceiptDetails receipt={selected} />}
      </Modal>
      <Modal
        open={quitting}
        onOpenChange={setQuitOpen}
        title="Quitter OMR Desktop ?"
        description="Le gateway local sera arrêté. Vos clients devront être reconnectés après un redémarrage."
      >
        <p>{state?.active ?? "?"} requête(s) en cours.</p>
        <Switch
          checked={force}
          onCheckedChange={setForce}
          label="J’accepte d’interrompre les requêtes en cours"
        />
        <div className="dialog-actions">
          <Button variant="secondary" onClick={() => setQuitOpen(false)}>
            Garder OMR ouvert
          </Button>
          <Button
            variant="destructive"
            disabled={busy}
            onClick={() => {
              const confirmed = force;
              setForce(false);
              void act(() => invoke("quit", { force: confirmed }));
            }}
          >
            Arrêter le moteur et quitter
          </Button>
        </div>
      </Modal>
    </div>
  );
}

export function ConnectionCard({
  connection: c,
  state,
  busy,
  change,
  remove,
  act,
}: {
  connection: Connection;
  state: Snapshot;
  busy: boolean;
  change: (c: Connection) => void;
  remove: () => void;
  act: <T>(
    action: () => Promise<T>,
    success?: string,
  ) => Promise<T | undefined>;
}) {
  const [secret, setSecret] = useState("");
  const [testModel, setTestModel] = useState<Model>();
  const [discovered, setDiscovered] = useState<string[]>();
  useEffect(() => setDiscovered(undefined), [c.url, c.transport]);
  const [removeOpen, setRemoveOpen] = useState(false);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const updateModel = (model: Model) =>
    change({
      ...c,
      models: c.models.map((m) => (m.id === model.id ? model : m)),
    });
  function addModel(upstream = "") {
    const model = newModel(upstream);
    setExpanded((value) => ({ ...value, [model.id]: true }));
    change({
      ...c,
      models: [...c.models, model],
    });
  }
  return (
    <Card className="connection">
      <div className="section-heading">
        <h2>{c.name}</h2>
        <Badge
          tone={
            state.connection_states[c.id]?.discovery === "reachable"
              ? "good"
              : ""
          }
        >
          {state.connection_states[c.id]?.discovery === "reachable"
            ? "Catalogue accessible"
            : state.connection_states[c.id]?.discovery === "failed"
              ? "Découverte échouée"
              : "Non testé"}
        </Badge>
        <Button
          variant="ghost"
          disabled={busy}
          onClick={() => setRemoveOpen(true)}
        >
          Retirer
        </Button>
      </div>
      <div className="form-grid">
        <details>
          <summary>Détails avancés · nom, URL et transport</summary>
          <Field label="Nom de la connexion">
            <Input
              value={c.name}
              disabled={busy}
              onChange={(e) => change({ ...c, name: e.target.value })}
            />
          </Field>
          <Field label="URL API · HTTP ou HTTPS /v1">
            <Input
              value={c.url}
              disabled={busy || !!c.subscription}
              onChange={(e) => change({ ...c, url: e.target.value })}
              placeholder="https://api.fournisseur.tld/v1"
            />
          </Field>
          <Field label="Transport fournisseur">
            <Select
              value={c.transport ?? "http"}
              disabled={busy || !!c.subscription}
              onValueChange={(value) =>
                change({ ...c, transport: value as "http" | "pi-ai" })
              }
              options={[
                { value: "pi-ai", label: "pi-ai · adaptateurs fournisseurs" },
                { value: "http", label: "HTTP direct · format inchangé" },
              ]}
            />
          </Field>
        </details>
      </div>
      {c.url.trim().toLowerCase().startsWith("http://") && (
        <p className="muted">
          HTTP ne chiffre ni les requêtes ni la clé API. Utilisez HTTPS sur un
          réseau non fiable.
        </p>
      )}
      {c.transport === "pi-ai" && !c.subscription && (
        <p className="muted">
          Clé API ou serveur local sans clé. Les abonnements Codex et Nous
          Portal utilisent leurs connexions dédiées. Les options non prises en
          charge sont refusées.
        </p>
      )}
      {c.subscription ? (
        <SubscriptionAccess
          connection={c}
          disabled={
            busy || !state.config.connections.some((saved) => saved.id === c.id)
          }
        />
      ) : (
        <div className="secret-row">
          <Field
            label={
              state.secret_states?.includes(c.id)
                ? "Clé présente dans le coffre OS"
                : "Clé API · optionnelle pour un serveur local"
            }
          >
            <Input
              type="password"
              value={secret}
              disabled={busy}
              autoComplete="off"
              placeholder="Jamais enregistrée dans la configuration"
              onChange={(e) => setSecret(e.target.value)}
            />
          </Field>
          <Button
            variant="secondary"
            disabled={busy || !secret}
            onClick={() =>
              void act(async () => {
                const value = secret;
                setSecret((current) => (current === value ? "" : current));
                await saveSecret(c.id, value);
              }, "Clé enregistrée dans le coffre OS.")
            }
          >
            Enregistrer dans le coffre OS
          </Button>
          {state.secret_states?.includes(c.id) && (
            <Button
              variant="ghost"
              disabled={busy}
              onClick={() =>
                void act(
                  () => saveSecret(c.id, ""),
                  "Clé retirée du coffre OS.",
                )
              }
            >
              Retirer la clé
            </Button>
          )}
        </div>
      )}
      <div className="section-heading">
        <Button
          variant="secondary"
          disabled={busy}
          onClick={() =>
            void act(async () =>
              setDiscovered(
                await command<string[]>({
                  command: "discover",
                  connection: c.id,
                }),
              ),
            )
          }
        >
          Découvrir les modèles
        </Button>
        <Button variant="ghost" onClick={() => addModel()}>
          <Plus size={16} />
          Déclarer un modèle
        </Button>
      </div>
      {discovered && (
        <ModelCatalogue connection={c} catalogue={discovered} change={change} />
      )}
      {!!c.models.length && (
        <div
          className="configured-models"
          role="region"
          aria-label="Modèles configurés"
          tabIndex={0}
        >
          {c.models.map((m) => (
            <details
              className="model"
              key={m.id}
              open={!!expanded[m.id]}
              onToggle={(event) => {
                const open = event.currentTarget.open;
                setExpanded((value) =>
                  value[m.id] === open ? value : { ...value, [m.id]: open },
                );
              }}
            >
              <summary>
                {m.upstream || "Nouveau modèle · identifiant requis"}{" "}
                <span className="muted">
                  {m.enabled ? "Activé" : "Désactivé"} ·{" "}
                  {state.model_states[m.id]?.generation === "verified"
                    ? "Génération vérifiée"
                    : state.model_states[m.id]?.generation === "failed"
                      ? "Génération échouée"
                      : "Non testé"}{" "}
                  · Réglages
                </span>
              </summary>
              {state.model_states[m.id]?.generation === "failed" &&
                state.model_states[m.id]?.generation_diagnostic && (
                  <p className="muted">
                    {errorMessage(
                      state.model_states[m.id].generation_diagnostic!.code,
                    )}
                  </p>
                )}
              {expanded[m.id] && (
                <>
                  <div className="section-heading">
                    <Field label="Identifiant exact du modèle amont">
                      <Input
                        value={m.upstream}
                        onChange={(e) =>
                          updateModel({
                            ...m,
                            upstream: e.target.value,
                            benchmark_model: "",
                            quality:
                              m.quality_mode === "benchmark" ? 0 : m.quality,
                          })
                        }
                        placeholder="vendor/model"
                      />
                    </Field>
                    <Badge>
                      {state.model_states[m.id]?.generation === "verified"
                        ? "Génération vérifiée"
                        : state.model_states[m.id]?.generation === "failed"
                          ? "Génération échouée"
                          : state.model_states[m.id]?.discovered
                            ? "Découvert · non testé"
                            : "Déclaré · non testé"}
                    </Badge>
                    <Button
                      variant="ghost"
                      onClick={() =>
                        change({
                          ...c,
                          models: c.models.filter((value) => value.id !== m.id),
                        })
                      }
                      aria-label={`Retirer le modèle ${m.upstream}`}
                    >
                      <X size={16} />
                    </Button>
                  </div>
                  <div className="model-switches">
                    <Switch
                      label="Autoriser cette route"
                      checked={m.enabled}
                      onCheckedChange={(enabled) =>
                        updateModel({ ...m, enabled })
                      }
                    />
                    <Switch
                      label="Outils compatibles (déclaré)"
                      checked={m.tools}
                      onCheckedChange={(tools) => updateModel({ ...m, tools })}
                    />
                  </div>
                  <div className="form-grid model-grid">
                    <Field label="Qualité déclarée">
                      <Select
                        value={
                          m.quality_mode === "benchmark"
                            ? "benchmark"
                            : String(m.quality)
                        }
                        onValueChange={(value) =>
                          updateModel(chooseQuality(m, value))
                        }
                        options={[
                          { value: "benchmark", label: "Benchmark externe" },
                          { value: "1", label: "1 · simple" },
                          { value: "2", label: "2 · intermédiaire" },
                          { value: "3", label: "3 · complexe" },
                        ]}
                      />
                    </Field>
                    <Field label="Effort transmis">
                      <Select
                        value={m.effort ?? ""}
                        onValueChange={(value) =>
                          updateModel({ ...m, effort: value || null })
                        }
                        options={[
                          { value: "", label: "Client / non imposé" },
                          ...[
                            "none",
                            "minimal",
                            "low",
                            "medium",
                            "high",
                            "xhigh",
                            "max",
                          ].map((value) => ({ value, label: value })),
                        ]}
                      />
                    </Field>
                    {(["input_price", "output_price"] as const).map(
                      (key, i) => (
                        <Field
                          key={key}
                          label={`${i === 0 ? "Entrée" : "Sortie"} · USD / M tokens`}
                        >
                          <Input
                            type="number"
                            min="0"
                            step="0.01"
                            value={m[key] ?? ""}
                            placeholder="Inconnu"
                            onChange={(e) =>
                              updateModel({
                                ...m,
                                [key]:
                                  e.target.value === ""
                                    ? null
                                    : Number(e.target.value),
                              })
                            }
                          />
                        </Field>
                      ),
                    )}
                  </div>
                  <div className="protocols">
                    <span>Protocoles déclarés :</span>
                    {[
                      ["chat", "Chat Completions"],
                      ["responses", "Responses"],
                      ["anthropic", "Messages"],
                    ].map(([id, name]) => (
                      <label key={id}>
                        <input
                          type="checkbox"
                          checked={m.protocols.includes(id)}
                          onChange={(e) =>
                            updateModel({
                              ...m,
                              protocols: e.target.checked
                                ? [...m.protocols, id]
                                : m.protocols.filter((value) => value !== id),
                            })
                          }
                        />
                        {name}
                      </label>
                    ))}
                  </div>
                  <div className="model-footer">
                    <code>{directId(c, m)}</code>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={
                        busy || !m.enabled || !m.protocols.includes("chat")
                      }
                      onClick={() => setTestModel(m)}
                    >
                      Tester
                    </Button>
                  </div>
                </>
              )}
            </details>
          ))}
        </div>
      )}
      <Modal
        open={!!testModel}
        onOpenChange={(open) => !open && setTestModel(undefined)}
        title="Tester ce modèle ?"
        description="Une génération courte sera envoyée à votre API. Elle peut consommer votre quota ou être facturée. Aucun autre modèle ne sera essayé."
      >
        <p>{testModel?.upstream}</p>
        <div className="dialog-actions">
          <Button variant="secondary" onClick={() => setTestModel(undefined)}>
            Annuler
          </Button>
          <Button
            disabled={busy}
            onClick={() => {
              const model = testModel!;
              setTestModel(undefined);
              void act(
                () =>
                  command({
                    command: "test_generation",
                    model: directId(c, model),
                    consent: true,
                  }),
                "Génération vérifiée. Reçu disponible dans l’inspecteur.",
              );
            }}
          >
            Lancer le test autorisé
          </Button>
        </div>
      </Modal>
      <Modal
        open={removeOpen}
        onOpenChange={setRemoveOpen}
        title="Retirer cette connexion ?"
        description="Ses modèles ne seront plus proposés après enregistrement. Sa clé reste dans le coffre OS : retirez-la séparément avant la connexion si nécessaire."
      >
        <div className="dialog-actions">
          <Button variant="secondary" onClick={() => setRemoveOpen(false)}>
            Annuler
          </Button>
          <Button variant="destructive" onClick={remove}>
            Retirer des réglages
          </Button>
        </div>
      </Modal>
    </Card>
  );
}
