# Rétablir le mouvement et les interactions de la landing

> Décision historique : [BILINGUAL-REFERENCE-REPAIR.md](BILINGUAL-REFERENCE-REPAIR.md) remplace notamment la boucle animée et la checkbox de pause.

## Écarts observés sur la base 9a6fa7c

La référence `brand/originals/Open_Model_Router_Landing_Page.zip` contient un flux SVG animé (`stroke-dashoffset`, cycle 2,5 s), une branche sélectionnée, un résultat de routage synchronisé avec les quatre choix du playground, une légère remise à plat du panneau au survol, des ancres, des FAQ natives, un menu mobile et la copie d’un exemple SDK. La capture utilisateur `upload_cdwnwdoz.png` montre notre panneau figé et la légende de fabrication rejetée.

Le prérendu actuel ne réhydrate aucun événement React. Mais il ne supprime pas une animation CSS : les styles et la synchronisation de la référence n’ont pas été portés. Les radios du guide fonctionnent déjà sans JS ; elles ne pilotent pas le hero. Ses branches sont un seul tracé sans sélection, son résultat reste générique. Ancres et FAQ fonctionnent. La navigation mobile est déjà visible, donc pas besoin de réintroduire un menu masquant les liens. Le SDK de référence est conceptuel : pas de bouton de copie pour une API inexistante.

## Contrat retenu

1. Garder la composition, les couleurs, les polices, les quatre profils et les composants prérendus. Utiliser le groupe radio existant comme source unique de sélection. CSS `body:has()` synchronise branche, carte, résultat du hero et panneau explicatif, y compris sans JavaScript.
2. Animer visiblement le trajet entrant et la seule sortie sélectionnée. Les segments restent reliés aux nœuds sur mobile. Ajouter une pause native au flux en boucle ; `prefers-reduced-motion` le rend statique tout en conservant sélection et focus. Aucun minuteur ou changement automatique de préférence.
3. Nommer le résultat « Profil sélectionné », pas modèle réel : aucune requête n’est envoyée. Lien du hero vers les choix ; navigation, FAQ, téléchargements et vérifications SHA-256 restent natifs. Restaurer le retour de profondeur au survol/focus, sans imposer un mouvement au touch.
4. Relire tout le contenu rendu et les métadonnées. Retirer la légende rejetée, le badge « Guide des profils · sans appel IA » et les remarques défensives redondantes du playground. Conserver les limites nécessaires : routage local ≠ hors ligne, accès à vérifier, clients en qualification, disponibilité et confiance des paquets, tokens observés/coûts estimés/économies non mesurées. Aucun chiffre ni capacité ajouté.

## Preuve et limite de livraison

Régressions d’abord : mouvement mesuré à deux instants dans Brave, état cohérent pour les quatre choix, copie sans vocabulaire de fabrication. Puis clavier, touch, pause, mouvement réduit, sans JS, breakpoints à ±1 px, clipping des contrôles et parcours complet existant avec téléchargements synthétiques isolés. Captures ordinaires et clip temporel portent sur le build local ; aucune publication ni installation. Candidat signé puis revue indépendante avant la continuation release `t_698bbc91`.
