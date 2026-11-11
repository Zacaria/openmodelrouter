# Registre de fidélité — travail en cours

> Historique : le titre « Pour chaque », la pause du flux et les adaptations de copie ne constituent plus le contrat courant. La décision [bilingue](BILINGUAL-REFERENCE-REPAIR.md) prime ; le contrôle précédent a confondu adaptation factuelle et traduction fidèle.

Base : `7184b0f6564d7188ac686b597e652cf5d8b5b86e` ; référence ZIP SHA-256 `71c59a4592cf8ac7b37ea04b125ef43ddb8b90e3c5e8455af8613a41733c456d`. Captures Brave réelles de la référence HTML et de la production à 1440 et 390 px : `site/artifacts/fidelity/` (preuves de travail ignorées, à conserver avant remise). Les captures complètes mobiles peuvent présenter des artefacts de composition ; vérifier avec des détails de viewport.

| Section / état | Référence et base publiée | Gravité / décision / validation |
| --- | --- | --- |
| Navigation et logo | Logo fourni distinct du pictogramme conceptuel ; production garde l'asset produit. La référence replie la navigation mobile. | Conserver l'identité fournie ; rétablir le menu mobile natif au clavier et sans JS, puis comparer les états ouvert et fermé. |
| Héros | Titre anglais sur trois lignes avec accent serif vert ; production « Vos modèles. Votre choix. ». | Critique : texte propriétaire exact « Pour chaque requête, le bon modèle », même hiérarchie ; test RED puis rendu desktop/mobile. |
| Graphe | Panneau orienté, branche active et flux ; production profils réels et contrôles de pause. | Adapter les noms réels, conserver synchronisation et pause ; comparer proportions et états. |
| Manifeste | Fond sauge et texte éditorial sur deux colonnes ; production reprend la composition avec contenu français. | Adaptation factuelle, contrôler espacement et texte à chaque largeur. |
| Sélecteur | Rail et trace, simulation signalée ; production profils réels avec carte et branche synchronisées, mais sans requête concrète. | Ajouter une requête d'exemple explicitement fictive, sans appel ni résultat inventé ; conserver profils et synchronisation. |
| Quatre cartes | Référence : embranchements, contrôles, routes et matrice de tuiles ; production : illustrations plus petites et textuelles. | Rétablir embranchements, contrôles qualitatifs et matrice sans pourcentages, fallback ni modèle inventés ; maintenir observé/estimé/non mesuré. |
| Intégration | Référence : panneau code noir avec barre de fenêtre et copie ; production : étapes Desktop, sans API fictive. | Conserver les étapes qualifiées, adopter le traitement de fenêtre sans créer de faux code ou de bouton Copier. |
| FAQ | Référence première réponse ouverte, plus/minus et règles ; production quatre questions fermées avec chevrons. | Ouvrir la première réponse et utiliser les indicateurs +/− natifs ; conserver les réponses réelles et le clavier. |
| CTA / téléchargements | Référence grand panneau lime et deux boutons ; production ajoute les vrais paquets, avertissements et empreintes. | Différence nécessaire ; conserver intégralement, vérifier par manifeste synthétique et captures mobiles. |
| Footer | Logo, description, règle et liens ; composition comparable mais logo différent. | Comparer dimensions et alignements. |

## Réconciliation des critiques

- Audit visuel `t_72f32323`, `rapport-fidelite.md` et `preuves-audit.zip` (SHA-256 du ZIP `235d016f196db3cce4a4ae5642e0aafc369d142e8b176d7628f084291784ef67`) : tous les secteurs du tableau ci-dessus ont été examinés. Les artefacts CDP de capture pleine page mobile ne sont pas traités comme des défauts réels ; utiliser les vues de section et viewport.
- Critique Claudio `t_96597d49`, `CRITIQUE-CLAUDIO-COPIE-INTERACTIONS.md` (SHA-256 `035bfd00c9a90ed50936ed22690a94502d31d050b1011f0c590c519bf86a4a42`) : titre et métadonnée, entrée « requête », CTA de navigation, explication du décideur, formulation des cartes, FAQ et clôture corrigés. Le slogan de marque fourni et les notices de confiance sont conservés ; la suggestion d'un titre final qui promettrait le « bon modèle » à chaque fois n'est pas reprise comme garantie supplémentaire.
- Le SDK et les données fictifs de la référence restent exclus. La fenêtre de parcours utilise des étapes Desktop réelles et ne comporte pas de faux bouton Copier. Les traces et les états de consommation sont qualitatifs ; aucune jauge chiffrée, économie ou bascule automatique n'est inventée. L'exemple fictif ne lance aucun appel.
- La navigation mobile native est repliable sans JavaScript et son icône change d'état. Contrairement à la référence JavaScript, elle ne se referme pas automatiquement au clic d'une ancre ; elle reste refermable au clavier ou au toucher. Ce compromis et les détails de mise en page restent à apprécier par la revue visuelle, pas considérés comme un PASS automatique.
- Le build sans manifeste n'active aucun téléchargement ; le staging utilise des octets synthétiques uniquement. Release doit relire le manifeste courant et conserver binaires, empreintes et avertissements réels avant publication.
