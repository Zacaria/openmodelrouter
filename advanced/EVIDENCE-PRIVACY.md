# Consommer uniquement les preuves expurgées

## Règle de consommation

Utiliser uniquement le nouvel index de confidentialité, le paquet source exact et le paquet de preuves dont les empreintes et tous les membres sont vérifiés. Le verdict reviewer doit porter sur ce nouveau SHA. Aucun ancien candidat n'a reçu de PASS ; l'intégration reste bloquée sur sa revue.

Les pièces jointes **78, 87, 94 et 95** sont non consommables, même si certaines ne contiennent pas l'adresse : elles décrivent les anciennes générations de preuves. La pièce 94 contient le texte de compte signalé par la revue ; ne pas la republier ni en afficher le contenu. Les outils Kanban disponibles n'exposent pas de retrait de pièce jointe. Leur présence historique n'est pas un effacement et le présent correctif ne modifie pas directement le stockage du board. Les contrats joints 39–41 restent valides.

## Transformation et provenance

Les captures locales JSON, JSONL et texte sont contrôlées hors ligne avec `advanced.evidence_privacy.redact_emails`. Pour le JSON, le document est décodé avant expurgation : l'échappement Unicode ne masque pas une adresse. Les nombres, valeurs nulles, structure et événements restent identiques ; seules les chaînes contenant une adresse de type email sont remplacées. Le registre joint conserve les hashes des octets avant/après, le nombre de remplacements et les chemins, sans conserver les valeurs supprimées. Les copies du texte dans `adapter_validation` et les extraits historiques sont aussi traités.

Les anciens conteneurs locaux de preuves sont retirés après extraction de leurs membres utiles uniques et enregistrement de leurs empreintes ; ils ne sont pas imbriqués dans les remplacements. Les manifestes historiques portent désormais sur les anciens octets : ils ne valident pas les nouveaux. Un nouveau manifeste vérifie chaque membre du paquet expurgé. Les sources des deux anciens candidats et les reçus CI ne sont pas des preuves natives de ce correctif.

Les générations natives restent rattachées à leurs sources d'origine (runs Codex/Claude 6, OMP 6/7 et historiques). Le code d'adapter fonctionnel est inchangé depuis `9346bf6` ; seuls le filtre, sa frontière de persistance et les régressions changent. Aucun nouvel appel fournisseur n'est nécessaire ni effectué. Les fixtures restent distinctes des captures natives transformées.

## Limites

Ce filtre ciblé retire les adresses usuelles non obfusquées. Il peut aussi masquer des placeholders de type paquet@version dans l'aide des commandes OMP ; aucun compteur numérique ni événement n'est supprimé. Il ne promet pas de détecter toutes les données personnelles, adresses obfusquées, noms ou secrets ; les diagnostics ne sont pas qualifiés comme canal privé. Les identifiants de sessions synthétiques et les identités des événements/outils restent utiles à la corrélation ; aucun identifiant de compte n'est requis pour l'analyse.

Hermes et délégation OMP restent non vérifiés. L'échec sémantique Claude et les coûts auxiliaires inconnus restent dans les résultats. Aucune activation, intégration desktop, dépense additionnelle ou release dans cette correction.
