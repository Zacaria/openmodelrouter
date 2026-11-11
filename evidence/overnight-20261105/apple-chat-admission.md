# Entrées privées Apple — Chat/classement 6b4d33b

## Décisions du coordinateur

- Base du pipeline : commit signé/revu `15a92a42ad787d652cffa6f14ea1dde49b446fd8` ; préserver chaque profil, pin, asset et chemin historiques.
- Nouvelle admission fermée : **`chat-6b4d33b`**. Réutiliser les validateurs communs ; ajouter un profil spécifique au nouveau candidat, pas une entrée libre/générique.
- Source du produit : `6b4d33b7272b2dc0124f12e0fe2acd2453bbe368`, tree `07589117ac3f0e469bcf6f1b60481e376c2ee0d4`, revue indépendante de fermeture PASS.
- Version produit `0.3.0`, cible `aarch64-apple-darwin`. Le nom canonique téléchargé par la lane reste `OMR-Desktop-0.3.0-aarch64-apple-darwin.dmg` ; l’asset d’entrée et le fichier DEV portent des noms distincts pour ne pas écraser les versions précédentes.
- Le wrapper natif, le sidecar et les ressources doivent être retrouvés dans l’inventaire exact du DMG. Ne pas reconstruire le produit ni modifier son source pendant cette admission.

## Assets exacts, déjà privés et relus

Dépôt `Zacaria/open-model-router`, visibilité privée vérifiée. Draft existant `desktop-v0.3.0-candidate.1`, release ID **431721137**, toujours draft après upload. Aucun ancien asset modifié, aucun `--clobber`.

| Asset d’entrée | ID | Octets | SHA-256 |
|---|---:|---:|---|
| `input-chat-6b4d33b-aarch64-apple-darwin.dmg` | 712264523 | 147870996 | `4dafd947d0b6c36b6a499d0aa7b337eabe65d2900fb621a02ea99989dd208666` |
| `input-chat-6b4d33b-aarch64-apple-darwin.unsigned.preflight.json` | 712264532 | 1092 | `416c120c6adbf0b77a0ac0d04ec164cbd31dba2d04149e0f8e579ff84beb904f` |

Chaque asset a été retéléchargé par son API ID et rehashé ; le digest GitHub concorde aussi. Rapport : `composed-candidate-04/signing-inputs/private-staging.json` dans ce dossier.

## Inventaire et preuves

`composed-candidate-04/chat-native-inventory.json` : **875 entrées**, SHA-256 `03f6d055bdb54b738060e387f06bc96e002d6601e7dea9a9fdcd2b613176cece`. Inventaire intégral produit depuis le DMG monté readonly, liens symboliques distingués des fichiers et répertoires. Volume détaché dans un `finally`.

`composed-candidate-04/chat-preflight.json` : reçu ci-dessus. Les PASS portent sur codesign ad hoc, empreinte réelle du sidecar et IPC du même sidecar empaqueté, avec 18 assertions OMP et 25 Chat. **Ce n’est pas une preuve d’interaction native WebView, de benchmark externe ou de Gatekeeper.** Le reçu les indique explicitement : GUI non exercée (écran verrouillé), benchmark synthétique, non notarisé, Gatekeeper exit 3. Le chemin réel du moteur est `Contents/MacOS/omr-engine`, SHA-256 `b436f9de6f48fac20dd8eaeb95a76444e5e441e3fea28a9b319eb910e99e3ea3`.

Conserver ces distinctions dans la validation et les attestations. Ne pas fabriquer de preuve native pour satisfaire un ancien schéma. Si le contrat impose un élément réellement absent, le signaler précisément ; les preuves et chemins existants permettent l’inspection indépendamment de la session verrouillée.

## Writer et revue

Worktree lié créé avant dispatch : `/srv/omr-private/workspaces/open-model-router/apple-chat-pins-6b4-20261105`, branche réelle `work/apple-chat-pins-6b4-20261105`, HEAD initial `15a92a42`. Aucun writer existant sur ce chemin.

Le tool primaire `kanban_create` ne permet pas de passer `branch_name`. Aucun shell `hermes kanban` n’est utilisé. La résolution native du checkout externe doit retourner exactement ce chemin et cette branche, sans fallback sous un dépôt ; vérifier ensuite la branche enregistrée par le dispatcher avant d’appeler le relais actif. Pas de nouveau clone.

Le builder ajoute l’admission et ses tests, pousse un commit signé privé et livre le diff exact. Le reviewer indépendant relit cet exact head en lecture seule avant la signature par t_3cc703cf. Aucun dispatch Apple, changement de quota, achat, publication publique ou remplacement d’installateur n’est autorisé dans la phase d’admission.
