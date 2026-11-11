# Vérification — mouvement et copie de la landing

> Historique du candidat précédent : la pause native et l’animation continue sont remplacées par la décision [bilingue](brand/decisions/BILINGUAL-REFERENCE-REPAIR.md), qui demande une introduction brève suivie d’un état stable et respecte le mouvement réduit.

## Candidat

`t_c284d78a`, base `9a6fa7cf8b7ffcbddb81a29b77bea6c7bedc8b88`, branche `work/landing-motion-copy-repair-v1`. Le commit signé exact et le readback de sa branche distante sont dans le handoff Kanban. Le [contrat](brand/decisions/LANDING-MOTION-COPY.md) compare la référence, le build et la capture utilisateur ; il complète les décisions précédentes sans changer l’identité visuelle.

## Correction

- Le prérendu ne supprime pas les animations CSS : le flux et la synchronisation de la référence n’avaient pas été portés. Entrée et seule sortie sélectionnée sont désormais animées ; les autres branches restent fixes. Les proportions du SVG et de la grille sont communes, y compris à 320 px ; les traits gardent leur épaisseur à l’échelle mobile.
- Le groupe radio existant pilote la branche, la carte, le résultat du hero et le panneau explicatif, sans JavaScript. Le résultat indique un **profil**, pas un modèle prétendument choisi par un appel réel. Le hero offre deux liens vers les choix. Pause native, mouvement réduit, retour de profondeur au survol/focus et bordures des cartes complètent les interactions ; ancres et FAQ restent natives.
- Copie relue dans le HTML rendu, les attributs accessibles et les métadonnées. Suppression de la légende rejetée, du badge de fabrication du guide, des commentaires défensifs et répétitions. Pour un paquet actif, l’état de génération distingue la génération vérifiée de la génération réelle non vérifiée, avec essais limités à un backend synthétique. L’état sans paquet conserve « à vérifier ». L’admission, les versions, tailles, empreintes, sources et états de confiance des paquets sont inchangés. Disponibilité, Gatekeeper, signature, clients en qualification, local ≠ hors ligne, coûts estimés et économies non mesurées restent explicites.

## Tests et preuves

RED avant modification : `artifacts/red/copy.log` échoue sur « pas une capture » ; `artifacts/red/motion.log` montre deux mesures `stroke-dashoffset = 0px` et échoue sur l’absence de mouvement. Après correction, les mêmes assertions passent.

Commandes finales : `npm run check`, `npm run format:check`, `npm run build`, `npm test`, `npm run test:browser`, `npm run test:staging`, `npm audit --audit-level=moderate`, suites de `.github/workflows/tests.yml` exécutées localement et `git diff --check`.

- Sept tests de téléchargement et sept contrats landing passent ; HTML construit validé. Aucune dépendance ajoutée ; audit npm : zéro vulnérabilité signalée.
- Suites canoniques : 64 racine, 16 pilot, 6 loop, 5 comparator, 9 integrated, 6 demo, 9 host-adapters et 7 landing. Un test pilot est explicitement sauté faute de modèle d’inférence locale configuré. Les échecs synthétiques internes de certification sont des assertions attendues de détection, pas des échecs de la suite finale.
- Brave 153.0.8010.37, Node 24.21.0, npm 11.19.0, Python 3.13.5. **76 états** : quatre profils × 19 largeurs, dont chaque breakpoint CSS à ±1 px. Branche/carte/résultat et panneau cohérents ; aucun texte ou contrôle hors largeur ni overflow masqué. Le parcours existant couvre aussi liens, FAQ et focus. Clavier, touch, sans JS et mouvement réduit passent.
- Deux instants et deux PNG distincts prouvent le déplacement réel de l’entrée et de la sortie active. Pause fige le déplacement, reprise le rétablit ; mouvement réduit le supprime sans masquer le contenu. Focus immédiat du contrôle de pause : contour solide 3 px, opacité 1, transition 0 s. Rapports `artifacts/motion/motion.json` et `artifacts/browser.json`, clip `artifacts/motion/routing.webm`.
- Axe A/AA 2.1/2.2 et bonnes pratiques : zéro violation à 390/1440 px. Le résultat de contraste incomplet sur fonds dégradés reste déclaré ; les enveloppes conservatrices `#304235` / `#b8d956` passent sur les quatre profils sans violation ni résultat incomplet. Zéro erreur console/réseau ni requête tierce.

Le staging reconstruit une copie temporaire minimale : deux formats Linux synthétiques admis, Mac bloqué et Windows non qualifié refusés, octets et checksums exacts par clic et clavier, puis retrait des fichiers périmés au rebuild sans manifeste. Il ne modifie pas le `dist/` habituel et ne qualifie aucun installateur réel. La matrice mouvement est aussi exécutée sur cet état actif.

## Inspection visuelle et capture

Captures complètes et viewports ordinaires desktop/mobile inspectés : hero, profils, capacités, parcours, FAQ et disponibilité. Le panneau reste fidèle au ZIP ; le flux est perceptible et sa branche active lisible. Les petits libellés techniques restent compacts sur mobile mais les contrôles ont une hauteur minimale de 44 px et les audits de contraste passent.

L’analyse automatique des images mobiles très hautes a d’abord signalé un faux chevauchement. Les crops des **pixels du même fichier** en haut et en bas montrent le hero normal puis la disponibilité et le footer normaux. Les viewports ordinaires et rectangles DOM confirment leur séparation ; aucun correctif produit ne s’appuie sur ce faux signal. Les crops sont conservés pour la revue. Les captures d’élément `flow-t0/t1` peuvent couper le débord décoratif du cadre ; le viewport complet prouve qu’il reste visible dans la page.

## Frontière de livraison

Pas de suppression de fichier source ni de données. Retirés : ancienne légende, badge/notice redondants et règles CSS devenues inutiles. Dépendances, build, captures, logs et replay restent ignorés ; preuves jointes à la carte, pas au payload. Le build par défaut reste l’allowlist de onze fichiers, sans JavaScript client, référence, preuve ni paquet de test. Le replay depuis le candidat Git doit produire les mêmes onze fichiers octet pour octet ; son résultat et ses hashes sont joints au handoff.

Revue indépendante obligatoire avant `t_698bbc91`. La release doit reconstruire avec le **manifeste courant** de `t_29098b54`, pas publier le build par défaut sans paquets de cette carte. Firefox/WebKit, lecteur d’écran, appareils physiques, fournisseur réel et installation native ne sont pas qualifiés ici. Aucun déploiement, activation de téléchargement, modification produit, achat, secret ou accès à des données client.
