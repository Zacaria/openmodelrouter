# Revue finale bornée — benchmark, 27 octobre 2026

## Verdict

**GO pour le commit de l'arbre exact `5530b4269bda1a9dfc94d00821343df588b97fcd`**, uniquement pour la fermeture du blocage documentaire de la revue précédente. Base de comparaison : arbre `134739f5141b3559adc722cfd16870fb155f86e1`. Ce verdict ne constitue pas un verdict final sur GOAL.md.

## Vérifications fraîches

- Le diff entre les deux objets Git, tous deux de type arbre, modifie uniquement `BENCHMARK-PILOT.md`, `BENCHMARK-V2.md` et `EDITORIAL-DRAFT.md` (7 ajouts, 1 suppression). Aucun code ni test n'a changé ; `git diff --check` ne signale rien.
- Le pilote et le brouillon éditorial sont explicitement qualifiés d'archives pré-campagne ; le brouillon n'est pas destiné à publication. Ils renvoient au protocole v2 et aux preuves locales. V2 situe sa rédaction avant les appels et distingue tâches synthétiques et inférence réelle, sans extrapoler aux abonnements ni aux intégrations. Le blocage identifié est clos.
- Les chemins cités `evidence/campaign/STUDY.md` et `evidence/campaign/attempt-2/` existent dans le dépôt canonique `/home/[REDACTED]/repos/open-model-router` ; le répertoire contient notamment plans, reçus, rapports, graphiques et manifeste. **Ces preuves sont non suivies dans le dépôt canonique et absentes de l'arbre à committer** : les références sont locales, pas des liens Git autoportants ni une garantie de disponibilité après clonage.
- L'index du worktree produisait l'arbre exact demandé à la vérification ; aucun changement non indexé sur fichiers suivis. Des répertoires `__pycache__` non suivis préexistaient et ne font pas partie de cet arbre. Aucun fichier source ni index n'a été modifié par cette revue.

## Portée et héritage

Revue précédente conservée : `benchmark-review.md`, SHA-256 `cc8346fe81572bb6236dc9775ba2ca8f2e9e4f4bdee63076cd30cc4a1a737841`. Ses vérifications benchmark, dont les 9 tests hors ligne et l'examen des reçus, sont **héritées**, non réexécutées ici ; les fichiers de code et de tests étant inchangés entre les deux arbres. Pas de réaudit général, d'appel fournisseur ni de nouvelle campagne. Les limites et réserves de la revue précédente restent applicables, notamment sur les configurations des bras, la provenance indépendante des appels et l'absence de conclusion générale ou de baseline d'abonnement.
