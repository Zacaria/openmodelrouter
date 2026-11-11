import { useState } from "react";
import { createRoot } from "react-dom/client";
import { Button, Field, Input, Modal, Select, Switch } from "./ui";

// Synthetic data only. Browser replay bundles the actual shared components.
export function ControlsFixture() {
  const [transport, setTransport] = useState("http");
  const [baseline, setBaseline] = useState("");
  const [period, setPeriod] = useState("1");
  const [open, setOpen] = useState(false);
  const [submitCount, setSubmitCount] = useState(0);
  return (
    <main style={{ margin: "auto", width: "100%", maxWidth: 720, padding: 30 }}>
      <h1>Fournisseur de test</h1>
      <form
        className="card"
        onSubmit={(event) => {
          event.preventDefault();
          setSubmitCount((count) => count + 1);
        }}
      >
        <div className="form-grid">
          <Field label="Nom">
            <Input name="name" placeholder="Connexion locale" />
          </Field>
          <Field label="Transport fournisseur">
            <Select
              name="transport"
              value={transport}
              onValueChange={setTransport}
              options={[
                { value: "http", label: "HTTP" },
                { value: "pi-ai", label: "pi-ai" },
                { value: "unavailable", label: "Indisponible", disabled: true },
                { value: "local", label: "Local" },
              ]}
            />
          </Field>
          <Field label="Qualité déclarée">
            <Input type="number" defaultValue={2} min={1} max={5} />
          </Field>
          <Field label="Chemin">
            <Input readOnly defaultValue="/synthetic/config.json" />
          </Field>
          <Field label="Indisponible">
            <Input disabled defaultValue="Non connecté" />
          </Field>
          <Field label="Sélecteur indisponible">
            <Select
              name="disabled-choice"
              value="offline"
              onValueChange={() => {}}
              options={[{ value: "offline", label: "Non connecté" }]}
              disabled
            />
          </Field>
        </div>
        <Field label="Modèle de référence">
          <Select
            name="baseline"
            value={baseline}
            onValueChange={setBaseline}
            options={[
              { value: "", label: "Aucune référence" },
              { value: "value:", label: "Valeur ressemblant à une sentinelle" },
              ...Array.from({ length: 40 }, (_, index) => ({
                value: `model-${index}`,
                label: `Fournisseur / Modèle synthétique ${index} avec un libellé volontairement long pour vérifier le défilement`,
              })),
            ]}
          />
        </Field>
        <Field label="Instruction">
          <textarea name="instruction" placeholder="Instruction synthétique" />
        </Field>
        <div className="protocols">
          <label>
            <input name="protocol" type="checkbox" />
            Chat JSON
          </label>
          <label>
            <input type="checkbox" disabled defaultChecked />
            Indisponible
          </label>
        </div>
        <Switch
          label="Activer la connexion"
          checked={false}
          onCheckedChange={() => {}}
        />
        <div className="dialog-actions">
          <Button type="button" variant="secondary">
            Annuler
          </Button>
          <Button disabled>Enregistrer</Button>
          <Button>Tester</Button>
        </div>
        <output data-testid="submit-count">{submitCount}</output>
      </form>
      <div className="filters">
        <label>
          Période
          <Select
            value={period}
            onValueChange={setPeriod}
            options={[
              { value: "1", label: "24 heures" },
              { value: "7", label: "7 jours" },
            ]}
          />
        </label>
      </div>
      <Button onClick={() => setOpen(true)}>Ouvrir le dialogue</Button>
      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Connexion synthétique"
        description="Fixture du menu dans un dialogue."
      >
        <Field label="Transport du dialogue">
          <Select
            value={transport}
            onValueChange={setTransport}
            options={[
              { value: "http", label: "HTTP" },
              { value: "pi-ai", label: "pi-ai" },
            ]}
          />
        </Field>
      </Modal>
    </main>
  );
}

if (typeof document !== "undefined") {
  const root = document.getElementById("root");
  if (root) createRoot(root).render(<ControlsFixture />);
}
