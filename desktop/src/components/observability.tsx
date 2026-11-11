import { ArrowRight, GitBranch, ShieldCheck } from "lucide-react";
import { Badge, Card } from "./ui";
import type { Config, Receipt } from "../types";

export const profileNames: Record<string, string> = {
  economy: "Économie",
  balanced: "Équilibré",
  quality: "Qualité",
};

export function Topology({
  config,
  receipts,
  revision,
}: {
  config: Config;
  receipts: Receipt[];
  revision: number;
}) {
  const count = config.connections
    .flatMap((c) => c.models)
    .filter((m) => m.enabled).length;
  const latest = receipts
    .filter((row) => row.mode !== "native")
    .reduce<Receipt | undefined>(
      (last, row) => (!last || row.timestamp > last.timestamp ? row : last),
      undefined,
    );
  return (
    <Card className="topology">
      <div className="section-heading">
        <h2>Topologie locale</h2>
        <Badge>CONFIGURATION r{revision}</Badge>
      </div>
      <div className="topology-canvas">
        <div className="topology-entry">
          <span className="eyebrow">ENTRÉE</span>
          <b>Votre client API</b>
          <small>Sur cet appareil</small>
        </div>
        <ArrowRight className="topology-arrow" size={20} aria-hidden="true" />
        <div className="topology-hub">
          <GitBranch size={26} />
          <b>OMR</b>
          <small>Catalogue local</small>
        </div>
        <div className="topology-routes">
          {Object.entries(profileNames).map(([id, name]) => (
            <div
              className="topology-route"
              key={id}
              data-selected={
                (latest?.mode === "automatic" && latest.profile === id) ||
                undefined
              }
            >
              <span>{name}</span>
              <code>omr/{id}</code>
            </div>
          ))}
          <div
            className="topology-route direct"
            data-selected={latest?.mode === "direct" || undefined}
          >
            <span>Direct</span>
            <small>
              {count} modèle{count > 1 ? "s" : ""} direct{count > 1 ? "s" : ""}{" "}
              autorisé{count > 1 ? "s" : ""}
            </small>
          </div>
        </div>
      </div>
      <div className="topology-caption">
        <span>
          {latest
            ? "Dernière requête observée · " +
              new Date(latest.timestamp * 1000).toLocaleString("fr-FR")
            : "Aucune route observée"}
        </span>
        <span>
          <ShieldCheck size={13} />
          {config.decider?.consent
            ? "Décideur consenti"
            : "Décideur non configuré"}
        </span>
      </div>
    </Card>
  );
}

export const statusNames: Record<string, string> = {
  completed: "Terminée",
  error: "Erreur",
  cancelled: "Annulée",
  blocked: "Bloquée",
};
const reasons: Record<string, string> = {
  continuity_cost: "Coût de continuité",
  task_requirement: "Exigence de la tâche",
  simple: "Tâche simple",
  fixed: "Route fixe",
};
export function ReceiptDetails({ receipt: r }: { receipt: Receipt }) {
  const unreconciledNative =
    r.native &&
    [r.native.thread_usage, r.native.last_call_usage].some(
      (value) =>
        typeof value.totalTokens === "number" &&
        typeof value.inputTokens === "number" &&
        typeof value.outputTokens === "number" &&
        value.totalTokens !== value.inputTokens + value.outputTokens,
    );
  const measured = (n: unknown, unit = "") =>
    typeof n === "number"
      ? `${n.toLocaleString("fr-FR")}${unit}`
      : "Non mesuré";
  return (
    <div className="receipt-detail">
      <div className="section-heading">
        <Badge tone={r.status === "completed" ? "good" : ""}>
          {statusNames[r.status] || r.status}
        </Badge>
        <code>{r.request_id}</code>
      </div>
      <dl className="detail-grid">
        <div>
          <dt>Route</dt>
          <dd>{r.route || "Non sélectionnée"}</dd>
        </div>
        <div>
          <dt>Modèle demandé</dt>
          <dd>{r.model_requested || "Non sélectionné"}</dd>
        </div>
        <div>
          <dt>Modèle confirmé</dt>
          <dd>{r.model_observed || "Non confirmé"}</dd>
        </div>
        <div>
          <dt>Mode</dt>
          <dd>
            {r.mode === "direct"
              ? "Direct · sans décideur"
              : r.mode === "native"
                ? "Session native isolée"
                : profileNames[r.profile || ""] || r.mode || "Inconnu"}
          </dd>
        </div>
        <div>
          <dt>Tokens entrée / sortie</dt>
          <dd>
            {measured(r.observed_input_tokens)} /{" "}
            {measured(r.observed_output_tokens)}
          </dd>
        </div>
        <div>
          <dt>Durée</dt>
          <dd>{measured(r.elapsed_ms, " ms")}</dd>
        </div>
      </dl>
      {r.native && (
        <div className="decision-trace">
          <h3>Opération native · {r.native.action}</h3>
          {unreconciledNative && (
            <p className="inline-error" role="note">
              Le total natif ne correspond pas aux sous-compteurs. Ces valeurs
              brutes ne prouvent pas une consommation nulle ; le coût de
              l’opération reste non mesuré.
            </p>
          )}
          <dl>
            <dt>Événements natifs</dt>
            <dd>
              {r.native.event_types.join(" · ") || "Aucun événement de tour"}
            </dd>
            <dt>Enfants terminés</dt>
            <dd>{r.native.completed_children}</dd>
            <dt>Permissions refusées · session</dt>
            <dd>{r.native.permission_denials}</dd>
            <dt>Snapshot du contexte natif</dt>
            <dd>
              <pre>{JSON.stringify(r.native.thread_usage, null, 2)}</pre>
            </dd>
            <dt>Dernier appel natif · pas le total du tour</dt>
            <dd>
              <pre>{JSON.stringify(r.native.last_call_usage, null, 2)}</pre>
            </dd>
            <dt>Coût auxiliaire / total / facture</dt>
            <dd>Non mesurés · aucun gain présumé</dd>
          </dl>
          <p className="muted">
            Snapshots non additionnables entre tours, exclus des totaux API.
            Modèle enfant non garanti ; aucun transcript conservé dans le reçu.
          </p>
        </div>
      )}
      {r.mode !== "native" && (
        <div className="decision-trace">
          <h3>Trace de décision</h3>
          <dl>
            <dt>Motif</dt>
            <dd>
              {typeof r.reason === "string"
                ? reasons[r.reason] || r.reason
                : r.mode === "direct"
                  ? "Accès direct · décideur contourné"
                  : "Non renseigné"}
            </dd>
            <dt>Modèles candidats</dt>
            <dd>
              {Array.isArray(r.candidates)
                ? r.candidates.join(" · ") || "Aucun"
                : "Non renseignés"}
            </dd>
            <dt>Décideur · durée / tokens</dt>
            <dd>
              {measured(r.decision_ms, " ms")} /{" "}
              {typeof r.decision_usage?.input_tokens === "number" &&
              typeof r.decision_usage?.output_tokens === "number"
                ? measured(
                    r.decision_usage.input_tokens +
                      r.decision_usage.output_tokens,
                  )
                : "Non mesuré"}
            </dd>
          </dl>
        </div>
      )}
      {r.error && (
        <p className="inline-error" role="alert">
          {r.error}
        </p>
      )}
      <details>
        <summary>Métadonnées complètes</summary>
        <pre>{JSON.stringify(r, null, 2)}</pre>
      </details>
    </div>
  );
}
