import { useState } from "react";
import { Button, Card, Field, Input, Select } from "./components/ui";
import {
  createProvider,
  providerPresets,
  type ApiProvider,
} from "./provider-presets";
import type { Connection, Snapshot } from "./types";

export function ProviderSetup({
  busy,
  add,
}: {
  busy: boolean;
  add: (connection: Connection) => void;
}) {
  const [type, setType] = useState<ApiProvider | "">("");
  const [url, setUrl] = useState("");
  return (
    <Card>
      <h2>Ajouter un fournisseur</h2>
      <Field label="Type de fournisseur">
        <Select
          value={type}
          onValueChange={(value) => {
            const next = value as typeof type;
            setType(next);
            setUrl(next ? providerPresets[next].url : "");
          }}
          disabled={busy}
          options={[
            { value: "", label: "Choisir un fournisseur" },

            ...Object.entries(providerPresets).map(([value, preset]) => ({
              value,
              label: preset.name,
            })),
          ]}
        />
      </Field>
      {
        <>
          {type && (
            <>
              <p>
                URL proposée : <code>{url}</code>.
              </p>
              {type !== "codex" && (
                <details>
                  <summary>Détails avancés · nouvelle connexion</summary>
                  <Field
                    label="URL de la nouvelle connexion"
                    hint="Renseignez l’URL avant l’ajout. Une destination enregistrée ne peut pas être remplacée avec le même identifiant de connexion."
                  >
                    <Input
                      value={url}
                      disabled={busy}
                      onChange={(event) => setUrl(event.target.value)}
                    />
                  </Field>
                </details>
              )}
            </>
          )}
          <Button
            disabled={busy || !type}
            onClick={() => {
              if (type) add({ ...createProvider(type), url });
            }}
          >
            Ajouter la connexion
          </Button>
          <p className="muted">
            Les réglages sont enregistrés automatiquement. Découvrez le
            catalogue, puis cochez les modèles à activer. Leurs capacités
            restent à déclarer.
          </p>
        </>
      }
    </Card>
  );
}

export function ConfigFilePanel({
  state,
  busy,
  dirty,
  load,
}: {
  state: Snapshot;
  busy: boolean;
  dirty: boolean;
  load: () => void;
}) {
  const file = state.config_file;
  if (!file) return null;
  const labels = {
    synced: "Fichier synchronisé",
    changed: "Fichier modifié · chargement requis",
    invalid: "Fichier invalide · dernière configuration valide conservée",
    unavailable:
      "Fichier inaccessible · dernière configuration valide conservée",
  };
  return (
    <Card>
      <h2>Configuration éditable</h2>
      <p>
        <code>{file.path}</code>
      </p>
      <p role="status">{labels[file.status]}</p>
      <p className="muted">
        Les réglages enregistrés dans OMR écrivent ce fichier. Après une
        modification externe, chargez-le ici. Les clés restent dans le coffre OS
        ; le fichier ne peut pas autoriser le décideur.
      </p>
      {dirty && (
        <p>
          Attendez l’enregistrement automatique. En cas de refus, corrigez les
          réglages ou abandonnez le brouillon avant de charger le fichier.
        </p>
      )}
      <Button variant="secondary" disabled={busy || dirty} onClick={load}>
        Charger le fichier
      </Button>
    </Card>
  );
}
