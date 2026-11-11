# OMR — mise à jour et compatibilité du 5 novembre 2026

**Source corrigée, revue et récupérable : `6b4d33b7272b2dc0124f12e0fe2acd2453bbe368`. La nouvelle version n’est pas encore publiée sur la landing.**

Le classement externe, le déclassement manuel et la navigation progressive sont construits. Les essais ci-dessous distinguent source exécutée, moteur empaqueté, frontend synthétique et installation publique. Ils ne clôturent pas `GOAL.md`.

## Compatibilité réellement exercée

| Hôte | Parcours exécuté ce matin | Résultat et limite |
|---|---|---|
| Hermes VM, 0.22.7 | Source OMR `6b4d33b` → Ollama réel, alias `omr-hermes-qwen3-4b:ctx8192` | Deux tours avec reprise du même identifiant natif, lecture/résultat d’outil, streaming, refus amont 502, annulation après texte réel et reprise : vérifications positives. L’erreur est visible dans l’adaptateur ; le client atteint son timeout 25 s. Pas de preuve d’erreur API native Hermes avant ce timeout. |
| Claude Code VM, 2.1.285 | Même source et même backend réel, protocole Messages | Deux tours, outil/résultat, streaming, erreur contrôlée, annulation et reprise : vérifications positives. Timeout d’erreur 25 s et événements retry conservés. |
| oh-my-pi Mac, 18.16.0 | Moteur **empaqueté exact** → D3 live `/v1/systemone` → Qwen réel | **18 vérifications positives** : deux tours, streaming, lecture d’un fichier synthétique, outil/résultat, annulation, refus sans décideur, garde de fichiers/écritures/réseau sur canaris. Ce n’est pas une connexion à l’instance UI personnelle. |
| Codex CLI Mac | Pas de nouveau tour lancé ; binaire natif présent au chemin Homebrew `0.166.0`, empreinte relevée | Le fonctionnement `--no-daemon -m open-model-router` est une observation propriétaire conservée sur `t_b8bd5fe8`, pas une qualification indépendante du nouveau moteur. Le raccord Chat Desktop reste soumis au blocage de confinement de `t_dac1e578`. Le wrapper Bun historique est cassé ; il n’a pas été réparé ni substitué au binaire natif. |
| Codex App | Aucun parcours indépendant nouveau | Usage GUI rapporté par le propriétaire, routage OMR de la GUI non établi indépendamment. Recherche `t_da4de6ee` terminée (pièce540), relecture Mac `t_121c02f5` (pièce541) : app26.1029.61003/build24614. Une piste HOME effectif est documentée, sans permission d'assouplir Seatbelt. |

Pour Hermes/Claude, les annulations donnent une sortie 130, un reçu `cancelled`, aucun membre vivant du groupe enfant et aucune socket amont encore établie. Cela ne démontre pas l’arrêt du calcul GPU. Le paramètre d’effort `none` est transmis ; son application par le backend n’est pas attestée. Les prompts/projets sont synthétiques, les homes/sessions séparés, les permissions du lanceur conservées. Les métadonnées de garde d’exécution sont conservées dans l’environnement des sous-processus.

## Chat et UX

- **25 vérifications live** des trois profils Économie/Équilibré/Qualité avec D3 et le moteur Mac exact : six tours terminés, contexte conservé, streaming, identité concrète, annulation et refus sans consentement. Le modèle Qwen de test possède un niveau manuel déclaré pour exercer les profils ; ce n’est pas une mesure de qualité externe ni la configuration personnelle.
- **16 vérifications interactives du frontend construit**, avec frontière native et catalogue benchmark explicitement synthétiques : navigation quotidienne/Avancé, clavier, polling, raccourci Inspecteur, éditions groupées, réponse tardive, correction manuelle, retour automatique et renommage d’un modèle qui efface sa référence benchmark et son niveau dérivé. Captures relues ; aucun débordement manifeste à la taille testée.
- **Suite Python : 332 cas, dont 3 ignorés, aucun échec**, avec les dépendances de build verrouillées déjà en cache ; **66 tests frontend**, TypeScript, format et build réussis. Le premier interpréteur navigateur ne possédait pas PyInstaller/packaging : ses deux erreurs d’environnement restent dans les logs, distinctes du passage vert dans le bon environnement.
- Revue indépendante initiale puis fermetures bornées : association périmée, page entièrement sans score, quota HTTP 200 et conservation du délai après catalogue invalide corrigés par régressions rouges puis vertes. Arbre final revu : `07589117ac3f0e469bcf6f1b60481e376c2ee0d4`.

Le benchmark externe réel reste **non mesuré : clé absente**. Aucun score n’a été inventé ni appel à l’API effectué. Les scores des captures sont des fixtures. Le défaut de clé ne bloque pas les essais de routage locaux.

## Paquet Mac exact

Le paquet DEV historique `omr-desktop-6b4d33b-macos-arm64-dev.dmg`
(147870996 octets, SHA-256 `4dafd947d0b6c36b6a499d0aa7b337eabe65d2900fb621a02ea99989dd208666`)
a été conservé. Son moteur était `b436f9de…e3ea3`, sa signature ad hoc et
Gatekeeper le refusait. Ce n'est pas le candidat final ci-dessous.

**Le DMG Chat final est signé et notarisé en privé** : 147945727 octets,
SHA-256 `e6ca38fd0d543435f806d8ccf774860ec31076de39f31b36a88f2ef897c2346a`.
Produit `6b4d33b`, pipeline source-only revu
`e4c1e07c5c642616d6ff6a908421686621d2a57a`, run privé `41981793495`,
artefact `13394486835`. Les six contrôles indépendants codesign, stapler et
Gatekeeper app/DMG passent ; les deux échecs CloudKit antérieurs sont conservés.
Rapport `t_3cc703cf/apple-41981793495/native-trust-passed-20261105T065200Z.json`
sous `/srv/omr-private/artifacts/open-model-router/`, SHA-256
`3d60296f663d9127ac533cf6b027eb415110cb3279434557dab070b2d84980e8`.

L'app finale a été copiée depuis un montage lecture seule et sa signature
revérifiée ; volume détaché, app personnelle non remplacée. Moteur signé
`032efbee15826579f8a47fd8750a4ae54102b54fdb1a5eaa83d6abaa0acb1b41` :

1. **OMP 18.16.0 : 18 contrôles verts sur les octets finaux**, avec D3/Qwen
   réels, deux tours, outil, streaming, annulation et erreur contrôlée.
2. **Chat IPC : 25 contrôles verts sur les octets finaux**, six tours des
   trois profils, contexte, D3 strict, streaming, annulation et refus sans
   consentement. L'IPC natif n'est pas une qualification GUI.
3. Configuration personnelle inchangée et aucun processus propre au rejeu restant.
   Ces tests vérifient l'absence de modèle Ollama étranger, pas un cache froid.

Preuves nouvelles sous `signed-6b4-replay/` dans le dossier durable de cette
carte : `stage.json`, `omp.json`, `chat.json`. Empreintes des deux derniers :
`edb3f4b5018cb7205027c28adbe7716ec262253409e18081db358eb70ebffa26` et
`84299c5293b16c34a785786461c1ecc3a43603f780ecc4c54a0bf4e50b873e4d`.
L'app reste 0.3.0 ARM64, minimum annoncé macOS 14.0. Aucun Mac Intel, macOS14
physique, installation utilisateur ni parcours GUI ne sont qualifiés ici.

## Landing et distribution

Les **quatre installateurs 0.1.0 existants** ont été retéléchargés anonymement depuis les liens de la landing : macOS ARM64, macOS x64, Windows x64 et Linux x64. Tous répondent HTTP 200 ; tailles, SHA-256 publiés et signatures binaires de format concordent. **Aucune installation de ces fichiers n’a été exécutée dans ce passage.** Ils ne contiennent pas cette mise à jour et n’ont pas été remplacés.

Ni Windows ni Linux n’ont été reconstruits avec cette source. La mise à jour publique exige encore les octets qualifiés, les parcours natifs/installés et le readback de la nouvelle distribution ; des téléchargements 0.1.0 intacts ne les remplacent pas.

## Reprise précise

1. **Admission/signature résolues : ne pas les recréer.** Consommer les octets signés et les preuves ci-dessus. La préparation du compagnon redistribuable exact (notices, matériaux et recette de remplacement) est confiée à `t_b4e6fcb5`, indépendamment de la GUI ; elle alimentera la publication existante `t_54b0a58f`.
2. Quand la session Mac est déverrouillée, présenter l’app finale puis vérifier l’UX native dans le cadre du parcours autorisé et de ses garanties d’isolation. Dernier relevé frais : écran réellement verrouillé. Aucun lancement GUI ni remplacement de l’app personnelle dans cette reprise ; les garanties manquantes du harnais existant ne sont pas déclarées closes.
3. Dans cette UI, appliquer les niveaux **déjà approuvés** Nemotron Super 3 / Lightning 2, puis exercer Équilibré et Qualité. Le snapshot privé révision23 antérieur montrait encore1/1 et un consentement D3 valide ; les essais isolés ne corrigent pas ce profil. Ne pas réclamer un nouveau consentement déjà acquis ni écrire le profil en parallèle.
4. Reprendre les cartes Codex existantes avec le rapport documentaire achevé et une barrière préventive réellement qualifiée pour la GUI. Un déverrouillage Mac seul ne ferme pas ce défaut technique. Aucun nouvel accord produit ni assouplissement de Seatbelt demandé.

## Preuves

La synthèse versionnée, les contrôles extraits et les empreintes de 28 preuves sont conservés dans `../evidence/overnight-20261105/`. Les rapports bruts, scripts réellement exécutés, binaires, logs longs et captures restent dans le dossier durable `/srv/omr-private/artifacts/open-model-router/chat-400-20261105/`, notamment `composed-candidate-04/`. La matrice téléchargeable est `compatibilite-omr-20261105.csv` dans ce dossier. Les sources signées sont sur la branche privée `work/chat-400-20261105`, ref distante relue.

La matrice à jour est [`COMPATIBILITY-20261105.csv`](COMPATIBILITY-20261105.csv) ; le CSV historique dans le dossier durable est conservé. La synthèse des nouveaux reçus signés est `../evidence/overnight-20261105/signed-final-replay.json`.

Aucun fichier source supprimé. Aucun secret, conversation privée, nouvel achat, assouplissement du sandbox, changement de visibilité du dépôt ou publication sociale. Le goal global reste ouvert.
