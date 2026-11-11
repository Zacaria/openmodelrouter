# Landing Ready — décision

## Source et périmètre

Importer fidèlement les deux HTML, CSS, JS et le logo du ZIP utilisateur `Open_Model_Router_Landing_Ready.zip`, SHA-256 `3a77d998d2ab638a8858e42ba03fb94c50453ecda041f17046c5bb0a1ec84053`. La base est la landing publiée `5ca70d5f0f30b16d6df3177ff37e3e14b8db5992`, pas le canonique sale. Aucun changement moteur ou installateur.

## Intégration

- Les templates du ZIP deviennent `src/templates/{en,fr}.html`, la CSS `src/ready.css` et le script `src/ready.mjs`. Le build conserve `/`, `/en/`, `/fr/`, fontes locales et liens de langue avec ancres.
- Le manifeste validé existant remplace le snapshot JSON et les lignes statiques exportées : version, OS, architecture, format, taille, SHA et source viennent du staging. Les quatre paquets historiques ne changent pas ; l’entrée de build ajoute seulement leur champ `prerelease` obligatoire, sans requalifier la release.
- Normaliser boutons, groupes nommés, liste native, focus du skip-link, ressources absolues et menu sans JS. Ne pas deviner une puce Mac, ni écraser un choix manuel avec un hint tardif ; permettre plusieurs formats. Ne pas restaurer les anciens choix stockés.
- Le script du ZIP garde ses scénarios explicatifs sans requête fournisseur. Les messages internes retirés par le propriétaire ne reviennent pas. Les notes utiles au téléchargement (préversion et avertissement Windows non signé) restent dans les détails du paquet, sans badge de statut dans le hero.

## Validation et autorité

Tester les deux langues aux cinq largeurs demandées, les scénarios, clavier, menu, synchronisation, SHA, absence de JS et détection conservative. Garder les refus de manifeste, les gardes de payload et le contrôle de tous les octets. L’ancien test de rendu rouge est observé avant implémentation.

Le constructeur ne déploie pas. Après revue indépendante de l’arbre exact, le coordinateur peut publier sous l’autorité existante de `GOAL.md`, puis vérifier publiquement pages, assets et téléchargements. Les preuves complètes sont attachées à la carte `t_bbb979de`.
