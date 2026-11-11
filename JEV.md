# Décideur Jev minimal

Adaptateur de décision autonome : il renvoie un identifiant de route, **ne lance pas de modèle** et ne prouve pas l'application du choix par un hôte. Documentation fournisseur : https://docs.typesafe.ai/api/system-one.md.

Fournir `TYPESAFE_API_KEY` par le gestionnaire de secrets natif de l'environnement ; aucun fichier `.env` n'est lu. Ne pas mettre la clé dans le dépôt ou les logs. `--public-prompts` est obligatoire : il atteste que le prompt est synthétique ou public et autorise son envoi externe à TypeSafe. Ne pas envoyer de données privées ou client. Les identifiants de route doivent être différents et désigner des routes configurées par l'appelant.

```sh
printf '%s' '{"prompt":"Return only the capital of France."}' | python3 jev_decider.py --direct-route DIRECT_ID --reasoning-route REASONING_ID --model jev-1.13.0 --public-prompts
```

Entrée : un objet JSON complet `{"prompt":"..."}` sur stdin, fermé après écriture ; taille maximale 65536 octets JSON. Sortie : un objet JSON sur stdout avec `route`, `model`, `usage` (tokens d'entrée et sortie) et `elapsed_ms`. En cas d'erreur, sortie non nulle, message générique sur stderr, rien sur stdout ; aucun repli ni nouvelle tentative automatique. Une erreur réseau après émission peut néanmoins avoir été facturée : ne pas relancer aveuglément.

Une seule requête HTTPS directe vers `api.typesafe.ai/v1/systemone`, sans proxy d'environnement, redirection ou retry. Réponse limitée à 65536 octets ; délai mural réseau de 15 s incluant DNS/TLS/lecture, via SIGALRM : exécuter sur Unix dans le thread principal. Le délai ne couvre pas l'attente de fermeture de stdin. Le modèle est épinglé à `jev-1.13.0` ; son identité, le choix, les probabilités, la confiance et l'usage sont vérifiés. Les instructions du prompt restent des données non fiables ; cela ne garantit pas l'absence d'injection ni la qualité de classification. L'appelant doit imposer ses propres limites de dépenses et vérifier que la route choisie est applicable.

Test hors ligne : `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest test_jev_decider -v`. Transport et réponses simulés, pas de fournisseur appelé.

Un seul smoke synthétique réel préexistant (`evidence/jev-smoke.json` dans le dépôt canonique) a rapporté **317,5 ms**, 363 tokens d'entrée et 33 de sortie. Ce point isolé n'est ni une latence générale, ni une mesure de qualité. Dépense et facture effectives inconnues ; aucun achat autorisé ou effectué dans ce travail.
