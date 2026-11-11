import { useEffect, useId, useRef, useState } from "react";
import { command, saveSecret } from "../api";
import { useNotify } from "../notifications";
import {
  applyBenchmarks,
  benchmarkMatch,
  benchmarkSecret,
  chooseQuality,
  modelListKey,
  type Benchmarks,
} from "../benchmark-ranking";
import type { Config, Model } from "../types";
import { Button, Card, Field, Input, Select } from "./ui";

const errors: Record<string, string> = {
  benchmark_key_required:
    "Ajoutez votre clé Artificial Analysis pour récupérer les scores.",
  benchmark_access_denied:
    "La clé n’a pas accès au catalogue gratuit. Vérifiez-la dans votre compte Artificial Analysis.",
  benchmark_rate_limited:
    "Le quota du benchmark est atteint. Les dernières données sont conservées.",
  benchmark_unavailable:
    "Le benchmark est indisponible. Les dernières données sont conservées.",
  benchmark_storage_unavailable:
    "Le cache n’a pas pu être enregistré. Les dernières données sont conservées.",
};

export function ModelRanking({
  config,
  change,
  visible,
  run,
}: {
  config: Config;
  change: (config: Config) => void;
  visible: boolean;
  run: <T>(action: () => Promise<T>) => Promise<T | undefined>;
}) {
  const notify = useNotify();
  const [data, setData] = useState<Benchmarks>();
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const running = useRef(false);
  const pending = useRef<boolean | null>(null);
  const latestRun = useRef(run);
  latestRun.current = run;
  const listKey = modelListKey(config);
  const optionsId = useId();
  async function refresh(force: boolean) {
    if (running.current) {
      pending.current = Boolean(pending.current || force);
      return;
    }
    running.current = true;
    setBusy(true);
    try {
      const result = await latestRun.current(() =>
        command<Benchmarks>({ command: "benchmark_refresh", force }),
      );
      if (result) {
        setData(result);
        if (force && result.error)
          notify(errors[result.error] ?? errors.benchmark_unavailable, "error");
      }
    } finally {
      running.current = false;
      setBusy(false);
      const queued = pending.current;
      pending.current = null;
      if (queued !== null) void refresh(queued);
    }
  }
  useEffect(() => {
    const timer = setTimeout(() => void refresh(false), 750);
    return () => clearTimeout(timer);
  }, [listKey]);
  useEffect(() => {
    if (!data) return;
    const next = applyBenchmarks(config, data);
    if (next !== config) change(next);
  }, [config, data]);
  function update(connection: string, model: Model) {
    change({
      ...config,
      connections: config.connections.map((c) =>
        c.id === connection
          ? {
              ...c,
              models: c.models.map((m) => (m.id === model.id ? model : m)),
            }
          : c,
      ),
    });
  }
  const rows = config.connections
    .flatMap((c) =>
      c.models.map((model) => ({
        connection: c,
        model,
        record: benchmarkMatch(model, data),
      })),
    )
    .sort(
      (a, b) =>
        (b.record?.score ?? -Infinity) - (a.record?.score ?? -Infinity) ||
        b.model.quality - a.model.quality ||
        a.model.upstream.localeCompare(b.model.upstream),
    );
  return (
    <section hidden={!visible} aria-label="Classement des modèles">
      <Card>
        <div className="section-heading">
          <div>
            <h2>Classement des modèles</h2>
            <p className="muted">
              Artificial Analysis · Intelligence Index
              {data?.version ? ` v${data.version}` : ""}
            </p>
          </div>
          <Button
            variant="secondary"
            disabled={busy}
            onClick={() => void refresh(true)}
          >
            {busy ? "Actualisation…" : "Actualiser le classement"}
          </Button>
        </div>
        <p className="muted">
          Les niveaux automatiques correspondent aux trois tranches du
          benchmark, pas à une garantie sur vos tâches. Vos réglages manuels
          restent prioritaires.
        </p>
        <p role="status">
          {data?.fetched_at
            ? `Données récupérées le ${new Date(data.fetched_at * 1000).toLocaleString("fr-FR")}.`
            : "Aucune donnée de benchmark chargée."}
        </p>
        {data?.error && (
          <p role="alert">
            {errors[data.error] ?? errors.benchmark_unavailable}
          </p>
        )}
        {Boolean(data?.retry_at) && (
          <p>
            Prochain accès possible le{" "}
            {new Date(data!.retry_at * 1000).toLocaleString("fr-FR")}.
          </p>
        )}
        <details>
          <summary>
            {data?.configured
              ? "Clé Artificial Analysis enregistrée"
              : "Connecter Artificial Analysis"}
          </summary>
          <p className="muted">
            Utilisez une clé de l’API gratuite pour votre usage interne. Elle
            reste dans le coffre OS ; aucune conversation ni liste de modèles
            n’est envoyée au benchmark.
          </p>
          <Field label="Clé API Artificial Analysis">
            <Input
              type="password"
              autoComplete="off"
              value={key}
              disabled={busy}
              onChange={(e) => setKey(e.target.value)}
            />
          </Field>
          <Button
            disabled={busy || !key}
            onClick={() =>
              void latestRun
                .current(async () => {
                  await saveSecret(benchmarkSecret, key);
                  setKey("");
                })
                .then(() => refresh(true))
            }
          >
            Enregistrer dans le coffre OS
          </Button>
        </details>
        <datalist id={optionsId}>
          {data?.models.map((m) => (
            <option key={m.slug} value={m.slug}>
              {m.name}
            </option>
          ))}
        </datalist>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Modèle</th>
                <th>Score externe</th>
                <th>Niveau de routage</th>
                <th>Référence du benchmark</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(({ connection, model, record }) => {
                return (
                  <tr key={`${connection.id}/${model.id}`}>
                    <td>
                      <strong>{model.upstream}</strong>
                      <small>
                        {connection.name}
                        {!model.enabled ? " · désactivé" : ""}
                      </small>
                    </td>
                    <td>
                      {record?.score == null
                        ? "Non classé par le benchmark"
                        : record.score.toLocaleString("fr-FR")}
                      {record && <small>{record.name}</small>}
                    </td>
                    <td>
                      <Select
                        aria-label={`Niveau de ${model.upstream}`}
                        value={
                          model.quality_mode === "benchmark"
                            ? "benchmark"
                            : String(model.quality)
                        }
                        onValueChange={(value) =>
                          update(
                            connection.id,
                            chooseQuality(model, value, record),
                          )
                        }
                        options={[
                          {
                            value: "benchmark",
                            label: `Automatique · ${record?.quality || "non classé"}`,
                          },
                          { value: "1", label: "1 · manuel" },
                          { value: "2", label: "2 · manuel" },
                          { value: "3", label: "3 · manuel" },
                        ]}
                      />
                    </td>
                    <td>
                      <Input
                        aria-label={`Référence benchmark de ${model.upstream}`}
                        list={optionsId}
                        value={model.benchmark_model ?? ""}
                        placeholder={model.upstream}
                        onChange={(e) =>
                          update(connection.id, {
                            ...model,
                            benchmark_model: e.target.value,
                          })
                        }
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!rows.length && (
          <p>Ajoutez des modèles depuis vos fournisseurs pour les classer.</p>
        )}
      </Card>
    </section>
  );
}
