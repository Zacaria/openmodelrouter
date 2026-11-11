# Open Model Router — candidate.3

Préversion privée, pas une livraison finale des quatre intégrations.

Source signée : `63e517c25caa503b02eb38b2be994f8e2c32e142`. Corrige la classification des délais après fermeture de la connexion amont et le signalement du délai après EOF en streaming. La classification d'un reset amont brut hors délai reste une limite connue.

- CI réussie sur ce commit. Installation isolée de l'archive : 114 tests réussis, un test d'inférence ignoré, contrôle landing réussi.
- Parcours synthétiques réels sur Hermes VM, Claude Code VM et Codex Mac : outils/résultats, reprise, streaming, modèle observé, erreur contrôlée et interruption/reprise. L'annulation Hermes a nécessité un essai ciblé ; le premier essai inconclusif est conservé. Une fermeture de socket ne prouve pas l'arrêt du calcul GPU. Les fins natives et les reçus de transport restent distincts.
- **oh-my-pi Mac non qualifié** : son préflight natif ne propose aucun modèle disponible. Authentification native ou backend utilisable requis avant les essais.
- Les résultats de benchmark restent bornés aux cas documentés ; aucune économie générale ou baisse de facture démontrée.

Archive SHA-256 : `44328fc6175cd1ac82527db0fd0b5d0788e381e1973643f55b082069261170bc`.

Les trois assets sont l'archive source, `manifest.json` et `SHA256SUMS`. Utiliser `build_release.py certify` avec un dépôt de confiance et le SHA complet attendu fourni séparément ; voir `INSTALL.md`. Ne pas extraire une archive non fiable directement avec tar. Aucun poids, abonnement, identifiant ou service automatique n'est installé.

Cette préversion ne remplace pas les assets de candidate.2, dont l'échec d'installation historique demeure conservé. L'objectif global reste ouvert.
