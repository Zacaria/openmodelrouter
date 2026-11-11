import { useState } from "react";
import { Joyride, type Step } from "react-joyride";
import { Button } from "./components/ui";
import { useErrorToast } from "./notifications";

const KEY = "omr:setup-tour:v1";
type Progress = { open: boolean; step: number };
export type TourPage =
  "Fournisseurs" | "Profils & règles" | "État" | "Inspecteur";

export function readTour(): Progress | null {
  try {
    const value = JSON.parse(localStorage.getItem(KEY) ?? "null");
    return value &&
      Object.keys(value).sort().join() === "open,step" &&
      typeof value.open === "boolean" &&
      Number.isInteger(value.step) &&
      value.step >= 0 &&
      value.step < 5
      ? value
      : null;
  } catch {
    return null;
  }
}
export function saveTour(open: boolean, step: number) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ open, step }));
  } catch {
    /* Tour progress is optional; provider settings use the native store. */
  }
}

export function setupSteps(navigate: (page: TourPage) => void): Step[] {
  const steps: {
    page: TourPage;
    id: string;
    title: string;
    content: string;
  }[] = [
    {
      page: "Fournisseurs",
      id: "providers",
      title: "Vos modèles, au même endroit",
      content:
        "Ajoutez vos accès Codex et Nous Portal, puis la connexion Jev avec sa clé API. Choisissez les modèles qu’OMR peut utiliser. Ajouter une connexion ne lance aucune génération.",
    },
    {
      page: "Profils & règles",
      id: "decider",
      title: "Jev choisit, vos modèles répondent",
      content:
        "Sélectionnez la connexion Jev, son protocole SystemOne et autorisez sa destination. Jev reçoit un extrait borné du contexte pour classer la tâche. Le test reste une action séparée.",
    },
    {
      page: "Profils & règles",
      id: "profiles",
      title: "Automatique ou modèle imposé",
      content:
        "Économie, Équilibré et Qualité expriment votre préférence. Un modèle direct ignore Jev. Le classement des modèles est modifiable ; un profil n’est pas une garantie de qualité.",
    },
    {
      page: "État",
      id: "client",
      title: "Utiliser OMR dans oh-my-pi",
      content:
        "Reliez oh-my-pi au moteur local, puis choisissez un profil OMR ou un modèle direct. L’accès reste sur cet appareil. Le port et la clé locale changent au redémarrage d’OMR.",
    },
    {
      page: "Inspecteur",
      id: "inspector",
      title: "Voir ce qui a réellement été exécuté",
      content:
        "Après votre première tâche, retrouvez le modèle utilisé, les tokens disponibles, la décision et les erreurs. Les reçus ne conservent pas le texte des conversations. Terminer cette visite ne lance aucun test.",
    },
  ];
  return steps.map(({ page, id, title, content }) => ({
    id,
    target: `[data-tour="${id}"]`,
    title,
    content,
    before: async () => {
      navigate(page);
    },
  }));
}

export function tourEvent(event: {
  type: string;
  index: number;
  status: string;
}) {
  const failed =
    event.type === "error:target_not_found" || event.type === "error";
  return {
    open: !failed && !["finished", "skipped"].includes(event.status),
    step: event.index,
    failed,
  };
}

export function SetupTour({
  navigate,
  close,
  initialStep,
}: {
  navigate: (page: TourPage) => void;
  close: () => void;
  initialStep: number;
}) {
  const [run, setRun] = useState(true);
  const [failed, setFailed] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  useErrorToast(
    failed !== null
      ? "Cette étape n’est pas accessible. Vos réglages sont conservés."
      : "",
  );
  return (
    <>
      {failed !== null && (
        <div className="alert error" role="alert">
          <span>
            Cette étape n’est pas accessible. Vos réglages sont conservés.
          </span>
          <Button
            onClick={() => {
              setAttempt(attempt + 1);
              setFailed(null);
              setRun(true);
            }}
          >
            Reprendre cette étape
          </Button>
          <Button variant="ghost" onClick={close}>
            Fermer la visite
          </Button>
        </div>
      )}
      <Joyride
        key={attempt}
        run={run}
        continuous
        initialStepIndex={failed ?? readTour()?.step ?? initialStep}
        steps={setupSteps(navigate)}
        options={{
          buttons: ["back", "skip", "primary"],
          skipBeacon: true,
          showProgress: true,
          blockTargetInteraction: false,
          disableFocusTrap: true,
          targetWaitTimeout: 3000,
          overlayClickAction: false,
          closeButtonAction: "skip",
          backgroundColor: "var(--panel)",
          textColor: "var(--text)",
          primaryColor: "var(--accent)",
          arrowColor: "var(--panel)",
          width: "min(380px, calc(100vw - 32px))",
          zIndex: 1000,
        }}
        locale={{
          back: "Précédent",
          next: "Suivant",
          nextWithProgress: "Suivant ({current}/{total})",
          last: "Terminer la visite",
          skip: "Passer la visite",
          close: "Fermer",
        }}
        onEvent={(event, controls) => {
          const progress = tourEvent(event);
          if (event.type === "tooltip") saveTour(true, progress.step);
          if (progress.failed) {
            controls.stop();
            setRun(false);
            setFailed(progress.step);
            saveTour(true, progress.step);
          } else if (!progress.open) {
            saveTour(false, progress.step);
            close();
          }
        }}
      />
    </>
  );
}
