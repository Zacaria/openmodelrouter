# Desktop — candidat UX fournisseurs du 4 novembre 2026

## Périmètre et décisions

Base produit : `8cf9a7f02a9c8bb77cc7cd6c505ab8f6b7a94795`. Cette tranche ne change ni moteur Python, ni Rust, ni dépendances/verrous, ni données/profil Mac. Contrat mis à jour avant les régressions : `PROVIDERS-FILE.md`.

- Un seul writer `ConfigAutosave` : debounce350 ms, coalescence, CAS sériel, réponse ancienne incapable de remplacer un brouillon récent, arrêt sur refus et relance explicite/correction. Abandon attend le writer puis relit la révision active.
- Clé, découverte et test vident d’abord la file. Aucun secret dans cette file ; seul le clic explicite utilise le coffre OS. Les erreurs restent visibles et annulent l’action dépendante.
- Catalogue avec Radix Checkbox existant, recherche et groupes OpenRouter, compteurs, portée complète de la recherche explicite même hors défilement. Les choix masqués, IDs et réglages retenus restent intacts. Les formulaires de modèles sont repliés et montés seulement à l’ouverture.
- Ajout actif, sans outils ou génération inventés. URL personnalisée saisissable avant l’ajout, car l’autosave lie dès son premier succès l’UUID à sa destination. Le contrôle de destination existant n’est pas contourné.
- Bouton `Tester`, consentement/coût conservés. Messages dédiés aux neuf codes moteur de `693c5141413da65c324014ce684d803f2614f420`, snapshot relu après erreur, résumé « Génération échouée » et diagnostic sûr. Le correctif moteur n’est pas inclus ici et exige sa propre revue avant composition.

## Vérifications réellement exécutées

Sur Linux, Node 24.21.0, Python 3.13.5 et Brave 153.0.8010.37 :

```sh
# Depuis desktop/
npm ci --ignore-scripts
npm ci --prefix provider-runtime --ignore-scripts
npm test
npm run check
npm run build
npm run test:build
npm run format:check
uv run --python 3.13.5 --with playwright==1.58.0 python scripts/test_provider_ux.py --evidence test-results/provider-ux
# Depuis la racine
python3 -m unittest test_desktop_provider_file test_desktop test_desktop_security test_desktop_onboarding test_desktop_review
uv run --python 3.13.5 --with ruff==0.17.3 ruff check --select F desktop/scripts/test_provider_ux.py desktop/scripts/native_replay.py desktop/scripts/onboarding_replay.py
uv run --python 3.13.5 --with ruff==0.17.3 ruff format --check desktop/scripts/test_provider_ux.py desktop/scripts/native_replay.py desktop/scripts/onboarding_replay.py
python3 -m py_compile desktop/scripts/test_provider_ux.py desktop/scripts/native_replay.py desktop/scripts/onboarding_replay.py
git diff --check
```

Résultats : **52 tests frontend**, types/build/format/stabilité des sources de build verts ; **60 tests Python** de persistance/sécurité/parcours verts. Aucun skip dans ces suites ciblées. Le build collecte93 notices ; ses assets restent ignorés, pas committés.

Le replay utilise **le frontend de production réel et Runtime isolé réel** pour sauvegarde, validation et CAS. Il vérifie604 identifiants, clavier Space, recherche insensible à la casse, sélection/effacement filtrés et conservation hors filtre, tout sélectionner sans montage de604 formulaires, écritures retardées sérialisées et dernière édition, coffre explicite après sauvegarde, sauvegarde avant découverte/test, refus invalide et conflits de révision/octets avec récupération. Dix groupes de contrôles sont consignés dans `test-results/provider-ux/report.json`. Captures clair/sombre à800/1180 px, sans débordement horizontal ; textes visibles revus sur les captures finales. Le diagnostic de génération est aussi exercé.

Découverte, génération et coffre de ce replay sont **des fixtures explicites** ; aucun appel fournisseur, coffre OS, token réel ou lecture de profil personnel. Le faux résultat de génération ne constitue pas une génération qualifiée. Les threads HTTP et fenêtres Brave du replay sont fermés à sa sortie.

RED observés : import du writer absent, méthodes run/discard absentes, découverte désactivée pour brouillon en attente ; catalogue absent ; champ URL avant ajout absent ; résumé replié masquant un échec ; neuf codes diagnostic non mappés. Puis GREEN. Le replay a aussi corrigé ses propres hypothèses de test : nom accessible avec aide de champ et chemin URL synthétique refusé par la validation existante ; pas d’assouplissement de production pour faire passer ces fixtures.

## Limites et remise

Pas de nouveau binaire Tauri/DMG, coffre réel, fournisseur réel ni qualification macOS exécutés. Les sélecteurs des deux anciens scripts natifs ont été adaptés et compilés syntaxiquement ; leurs campagnes natives ne sont pas revendiquées. La suite Python racine exhaustive n’a pas été exécutée pour ce delta frontend ; suites ciblées ci-dessus uniquement. Le premier build sans notices a refusé comme prévu ; installation verrouillée de provider-runtime, puis build réussi. Playwright/Ruff sont test-only via uv, aucune dépendance produit ajoutée.

Supprimés : bouton Appliquer, mur de boutons découvert et son CSS, verrous dirty silencieux des actions, props dirty devenues inutiles, activation manuelle redondante et anciens libellés des scripts. Aucun fichier source entier, base ou donnée utilisateur supprimé.

Après revue indépendante exacte, transmettre à `t_0fcc8c66` pour composition avec la tranche moteur revue, build Mac DEV et essai manuel propriétaire. `desktop/src/App.tsx` est un hotspot avec le petit raccord Chat de `t_ac9f56cc` : intégrer ses seuls hunks navigation sans recopier l’ancienne orchestration. Aucun changement de son worktree et aucune attente Chat imposée à cette remise.
