# Pilote local mixte

Ce pilote utilise la véritable classification s1d1 locale sur le premier message utilisateur, suivie d'une génération simulée. Le bras configurable utilise une commande locale explicite ; le bras défaut utilise directement le générateur simulé. Il ne démontre ni intégration OMP, ni qualité de génération réelle, ni économie. Les commandes configurées sont de confiance et ne constituent pas une isolation système. Ne pas fournir de données privées ou utiliser des commandes distantes ou payantes.

`pilot_arm.py ARM CONFIG` lit une requête JSON sur stdin et produit le format attendu par `benchmark.py`. Le chemin des poids doit désigner une copie locale épinglée ; aucun téléchargement implicite. Les reçus de génération et les prix sont synthétiques. Pour le bras s1d1, seule la classification est réelle ; les autres bras et la génération sont simulés. Les compteurs de décision et énergie restent inconnus ; les valeurs zéro du générateur simulé ne constituent pas une facture ni une mesure locale.

Le pilote n'évalue pas les capacités d'outils, sous-agents ou continuité d'un hôte. Les autorisations, le repli, le contexte minimal côté générateur et les efforts restent à implémenter et vérifier avant un usage réel. Ne pas interpréter ce pilote comme validant ces garde-fous.
