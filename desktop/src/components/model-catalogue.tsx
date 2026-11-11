import { useId, useState } from "react";
import { Checkbox } from "radix-ui";
import { Check } from "lucide-react";
import { Button, Field, Input } from "./ui";
import type { Connection, Model } from "../types";

export function newModel(upstream = ""): Model {
  return {
    id: crypto.randomUUID(),
    upstream,
    protocols: ["chat"],
    enabled: true,
    tools: false,
    quality: 0,
    quality_mode: "benchmark",
    input_price: null,
    output_price: null,
    effort: null,
  };
}
export function selectModels(
  models: Model[],
  ids: string[],
  selected: boolean,
): Model[] {
  const targets = new Set(ids);
  if (!selected) return models.filter((model) => !targets.has(model.upstream));
  const existing = new Set(models.map((model) => model.upstream));
  return [
    ...models,
    ...[...targets].filter((id) => !existing.has(id)).map((id) => newModel(id)),
  ];
}
export function catalogueGroups(
  connection: Connection,
  catalogue: string[],
  query: string,
) {
  let openrouter = false;
  try {
    openrouter = new URL(connection.url).hostname === "openrouter.ai";
  } catch {
    /* invalid draft URL */
  }
  const groups = new Map<string, string[]>();
  const search = query.trim().toLocaleLowerCase();
  for (const id of new Set(catalogue)) {
    if (!id.toLocaleLowerCase().includes(search)) continue;
    const name =
      openrouter && id.includes("/") ? id.split("/")[0] : connection.name;
    const group = groups.get(name) ?? [];
    group.push(id);
    groups.set(name, group);
  }
  return [...groups]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, ids]) => ({ name, ids }));
}
export function ModelCatalogue({
  connection,
  catalogue,
  change,
}: {
  connection: Connection;
  catalogue: string[];
  change: (connection: Connection) => void;
}) {
  const [query, setQuery] = useState("");
  const scopeId = useId();
  const groups = catalogueGroups(connection, catalogue, query);
  const visible = groups.flatMap((group) => group.ids);
  const all = [...new Set(catalogue)];
  const selected = new Set(connection.models.map((model) => model.upstream));
  const selectedCount = all.filter((id) => selected.has(id)).length;
  const visibleSelected = visible.filter((id) => selected.has(id)).length;
  function choose(ids: string[], value: boolean) {
    change({
      ...connection,
      models: selectModels(connection.models, ids, value),
    });
  }
  return (
    <section className="model-catalogue" aria-label="Catalogue découvert">
      <div className="section-heading">
        <strong>Modèles annoncés par l’API</strong>
        <span role="status" aria-live="polite">
          {selectedCount} / {all.length} sélectionnés
        </span>
      </div>
      <p className="muted">
        Capacités non vérifiées. Cocher ajoute et active la route ; aucun test
        n’est lancé.
      </p>
      <Field label="Rechercher un modèle">
        <Input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Nom ou fournisseur…"
        />
      </Field>
      <div
        className="catalogue-scroll"
        role="region"
        aria-label="Résultats du catalogue"
        tabIndex={0}
      >
        {groups.map(({ name, ids }) => (
          <fieldset className="catalogue-group" key={name}>
            <legend>
              {name}{" "}
              <span>
                {ids.filter((id) => selected.has(id)).length} / {ids.length}{" "}
                sélectionnés
              </span>
            </legend>
            {ids.map((id) => (
              <label className="catalogue-option" key={id}>
                <Checkbox.Root
                  className="checkbox"
                  checked={selected.has(id)}
                  onCheckedChange={(value) => choose([id], value === true)}
                >
                  <Checkbox.Indicator>
                    <Check size={14} aria-hidden="true" />
                  </Checkbox.Indicator>
                </Checkbox.Root>
                <span>{id}</span>
              </label>
            ))}
          </fieldset>
        ))}
        {!visible.length && (
          <p>
            {all.length
              ? "Aucun résultat pour cette recherche."
              : "Aucun modèle annoncé. Vous pouvez le déclarer manuellement."}
          </p>
        )}
      </div>
      <div className="catalogue-footer">
        <small id={scopeId}>
          {visible.length} résultats de recherche · actions sur ces{" "}
          {visible.length} modèles, y compris hors défilement
        </small>
        <div className="actions">
          <Button
            variant="ghost"
            size="sm"
            aria-describedby={scopeId}
            title={`Désélectionner les ${visible.length} résultats de recherche`}
            disabled={!visibleSelected}
            onClick={() => choose(visible, false)}
          >
            Effacer
          </Button>
          <Button
            variant="secondary"
            size="sm"
            aria-describedby={scopeId}
            disabled={!visible.length || visibleSelected === visible.length}
            onClick={() => choose(visible, true)}
          >
            Tout sélectionner
          </Button>
        </div>
      </div>
    </section>
  );
}
