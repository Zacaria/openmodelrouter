# Candidat natif macOS — 2 novembre 2026

## Contrat

La carte `t_5c86c079` part du checkpoint signé `d619cd75d069a616ad33605a77e720c878528247`, non approuvé globalement. Elle prépare une application autonome sur mac-worker : onboarding, transport pi-ai, décideur géré et arrêt. Aucun PASS Linux ou ancien paquet macOS n'est hérité. Windows et le kit Linux ne sont pas des prérequis.

Réutiliser `scripts/build_sidecar.py`, les locks et harnais existants. Ne pas modifier les workflows communs, détenus par le worker Windows. Préparer les dépendances natives verrouillées et vérifier leurs imports dans le moteur gelé. Conserver les contrôles d'intégrité et refus de provenance existants ; distinguer les obligations des composants effectivement embarqués des affirmations de reconstruction historique non démontrées.

## Embarquement ARM macOS

Le build macOS installe lui aussi les dépendances du décideur depuis un wheelhouse fourni par `OMR_WORKER_WHEELS`, hors réseau et avec `desktop/s1d1-requirements.lock`. Le lock existant contient déjà les mêmes versions et empreintes pour ARM macOS : aucun deuxième lock n'est nécessaire. ONNX Runtime 1.31.1 fournit une roue ARM pour macOS 14+, pas une preuve Intel/Rosetta. La compilation native et l'import du worker gelé sont rapportés avec leurs empreintes dans [la qualification privée](../evidence/native/macos-20261102/VERIFICATION.md). Ne pas confondre le refus de provenance du kit Linux avec l'installation de ces dépendances pour une qualification locale non publiée. Le manifeste du pont utilise les noms de cible Bun épinglés (`aarch64`), distincts du nom d'architecture npm de l'addon (`arm64`).

## Exécution et preuves

Construire en série dans un dossier dédié de mac-worker, après vérification de sa charge. Ne pas arrêter les applications ou sessions personnelles. État, cache et coffre de test isolés ; aucune clé personnelle ou souscription importée. Exercer la configuration dans l'interface, direct, routage, inspecteur et arrêt sur les octets exacts. Un répondant synthétique et une vraie inférence locale sur poids déjà présents sont des preuves distinctes.

Les runtimes Python, Bun et l'addon pi-ai sont embarqués ; Node/Python ne sont pas des prérequis utilisateur. ARM natif et Intel/Rosetta ne sont pas interchangeables. Garder les empreintes du paquet, logs et captures dans un stockage durable lié à la carte, et conserver les changements source en commits signés.

## Autorité et remise

Aucune publication, dépense, export de secret, substitution à l'app personnelle ou contournement SSH/OS. La signature du commit ne constitue pas une signature Developer ID, une notarisation ou une admission Gatekeeper. La revue indépendante porte sur ce candidat exact avant la livraison de `t_c350e5cc` ; la carte demande une revue par `reviewer`. Les résultats, limites et commandes seront consignés séparément des instructions et de la copie publique.
