# Open Model Router — analyse de la campagne figée

Analyse hors Git, sans appel fournisseur ni réexécution du benchmark. Sources locales : `evidence/campaign/STUDY.md`, plans, JSONL, reçus gateway et manifestes ; chemins complets et SHA-256 dans `MANIFEST.sha256`. Données synthétiques uniquement.

## Périmètre et intégrité

- Deux jeux × cinq familles × deux répétitions × trois bras = 60 parcours prévus et 60 reçus pour chaque tentative. Plans comparés ligne par ligne aux résultats (identité, ordre local et global), sans manque ni doublon ; graines dev 27, validation 28. Plans byte-identiques entre tentatives.
- Les manifestes déclarent les mêmes SHA-256 pour les trois fichiers communs gateway, benchmark et adaptateur Jev ; le hash de STUDY correspond au premier manifeste. Ceci vérifie la concordance des déclarations, pas les octets des scripts externes, hors périmètre de lecture. Plans et empreintes fixture identiques ; les fixtures elles-mêmes ne sont pas incluses ici. Les configurations comparées diffèrent uniquement par le chemin de reçus et, pour configurable, le chemin interpréteur. Cela ne prouve pas indépendamment le contenu des scripts externes ou l’ensemble des prompts.
- Tentative 1 : 20 erreurs HTTPError côté runner pour configurable et 20 reçus gateway invalid_request. Le chemin interpréteur du fichier de configuration contient littéralement quatre astérisques ; le second n’en contient pas. Le contexte de campagne attribue l’échec à FileNotFound et une résolution native dans le même processus à la correction ; les reçus publics ici ne contiennent ni traceback FileNotFound ni preuve autonome du mécanisme. Les sorties de l’outil peuvent masquer le chemin même lorsqu’il est correct. Aucun secret affiché.
- Référence : alias local Hermes `omr-hermes-qwen3-4b:ctx8192`, effort transmis `none`, pas le modèle natif par défaut de ChatGPT. Route alternative `qwen3:4b`, effort backend non forcé. s1d1 est expérimental, seuil 0,35 ; configurable utilise Jev. Pas de comparaison avec un abonnement commercial.

## Résultats de la tentative 2

| Jeu | Famille | Bras | Pass | Fail | Erreur (raison) | Durée ms : somme / moyenne / écart-type population / min–max |
|---|---|---|---:|---:|---|---|
| dev | simple | default | 2 | 0 | {} | 1806.1 / 903.0 / 856.4 / 46.7–1759.4 (n=2) |
| dev | simple | s1d1 | 2 | 0 | {} | 189.0 / 94.5 / 2.7 / 91.8–97.2 (n=2) |
| dev | simple | configurable | 2 | 0 | {} | 2635.3 / 1317.7 / 29.1 / 1288.5–1346.8 (n=2) |
| dev | code | default | 2 | 0 | {} | 192.7 / 96.3 / 1.6 / 94.7–98.0 (n=2) |
| dev | code | s1d1 | 2 | 0 | {} | 224.3 / 112.1 / 1.6 / 110.5–113.8 (n=2) |
| dev | code | configurable | 2 | 0 | {} | 2590.1 / 1295.1 / 71.0 / 1224.0–1366.1 (n=2) |
| dev | diagnostic | default | 0 | 2 | {} | 833.6 / 416.8 / 4.6 / 412.2–421.5 (n=2) |
| dev | diagnostic | s1d1 | 0 | 2 | {} | 840.6 / 420.3 / 7.0 / 413.3–427.3 (n=2) |
| dev | diagnostic | configurable | 0 | 2 | {} | 3134.2 / 1567.1 / 18.2 / 1548.9–1585.3 (n=2) |
| dev | conversation | default | 2 | 0 | {} | 215.8 / 107.9 / 0.0 / 107.9–107.9 (n=2) |
| dev | conversation | s1d1 | 2 | 0 | {} | 231.9 / 115.9 / 2.4 / 113.5–118.3 (n=2) |
| dev | conversation | configurable | 2 | 0 | {} | 2567.0 / 1283.5 / 17.1 / 1266.4–1300.6 (n=2) |
| dev | agents | default | 0 | 0 | {'ValueError': 2} | 2820.5 / 1410.3 / 1242.9 / 167.4–2653.2 (n=2) |
| dev | agents | s1d1 | 0 | 2 | {} | 4972.4 / 2486.2 / 1242.2 / 1244.0–3728.4 (n=2) |
| dev | agents | configurable | 0 | 0 | {'ValueError': 2} | 2699.6 / 1349.8 / 53.5 / 1296.3–1403.3 (n=2) |
| validation | simple | default | 2 | 0 | {} | 87.3 / 43.7 / 0.1 / 43.6–43.7 (n=2) |
| validation | simple | s1d1 | 2 | 0 | {} | 139.6 / 69.8 / 14.5 / 55.3–84.4 (n=2) |
| validation | simple | configurable | 2 | 0 | {} | 2348.2 / 1174.1 / 0.7 / 1173.4–1174.9 (n=2) |
| validation | code | default | 2 | 0 | {} | 200.0 / 100.0 / 0.2 / 99.8–100.1 (n=2) |
| validation | code | s1d1 | 2 | 0 | {} | 253.9 / 127.0 / 5.6 / 121.4–132.6 (n=2) |
| validation | code | configurable | 2 | 0 | {} | 2499.4 / 1249.7 / 20.6 / 1229.1–1270.3 (n=2) |
| validation | diagnostic | default | 0 | 2 | {} | 839.5 / 419.8 / 22.3 / 397.5–442.0 (n=2) |
| validation | diagnostic | s1d1 | 0 | 2 | {} | 848.8 / 424.4 / 5.9 / 418.5–430.3 (n=2) |
| validation | diagnostic | configurable | 0 | 2 | {} | 3064.3 / 1532.1 / 37.7 / 1494.4–1569.9 (n=2) |
| validation | conversation | default | 2 | 0 | {} | 260.6 / 130.3 / 1.5 / 128.8–131.8 (n=2) |
| validation | conversation | s1d1 | 2 | 0 | {} | 249.2 / 124.6 / 1.5 / 123.1–126.1 (n=2) |
| validation | conversation | configurable | 2 | 0 | {} | 2596.7 / 1298.4 / 25.0 / 1273.4–1323.3 (n=2) |
| validation | agents | default | 2 | 0 | {} | 777.1 / 388.6 / 1.9 / 386.7–390.5 (n=2) |
| validation | agents | s1d1 | 0 | 2 | {} | 7498.7 / 3749.3 / 14.2 / 3735.2–3763.5 (n=2) |
| validation | agents | configurable | 2 | 0 | {} | 7758.1 / 3879.0 / 1270.3 / 2608.7–5149.4 (n=2) |

Fail signifie évaluation négative ; erreur signifie parcours non évalué, pas un fail converti. Les 12 diagnostics sont `fail` : la sortie brute contient une première hypothèse JSON, le résultat outil `dns`, puis une sortie intermédiaire vide et une réponse finale JSON `{"cause": "dns", "evidence": "dns"}`. Les reçus ne donnent pas de motif de parse précis (`reason` est null) : ne pas prétendre identifier le parseur fautif depuis ces seules preuves. En agents dev, default et configurable ont chacun deux `ValueError` avec sortie parent vide ; s1d1 a deux fail avec sortie vide. En validation, default et configurable réussissent les deux délégations ; s1d1 échoue deux fois.

Code : les 12 reçus exécutés rapportent chacun quatre tests AST comportementaux effectivement évalués, tous réussis (48 résultats). Ils ne constituent pas une sandbox générale. La délégation est orchestrée par le runner, pas une validation des sous-agents natifs des hôtes.

## Usage observé par bras

Somme / moyenne / écart-type population / min–max ; `n` compte les valeurs connues sur 20 parcours. Les tokens cache peuvent être inclus dans input ; reasoning peut être inclus dans output. Ne pas additionner ces catégories comme des totaux indépendants.

| Bras | Mesure | Statistiques |
|---|---|---|
| default | input | 7466.0 / 373.3 / 216.4 / 163.0–716.0 (n=20) |
| default | output | 500.0 / 25.0 / 23.3 / 2.0–61.0 (n=20) |
| default | cache_read | 6615.0 / 330.8 / 219.6 / 0.0–667.0 (n=20) |
| default | cache_write | inconnu (0) |
| default | reasoning | inconnu (0) |
| default | decision | inconnu (0) |
| default | tools | inconnu (0) |
| default | retry | inconnu (0) |
| default | elapsed_ms | 8033.2 / 401.7 / 634.1 / 43.6–2653.2 (n=20) |
| default | decision_ms | 0.1 / 0.0 / 0.0 / 0.0–0.0 (n=20) |
| default | retries | 0.0 / 0.0 / 0.0 / 0.0–0.0 (n=20) |
| s1d1 | input | 6606.0 / 330.3 / 203.5 / 163.0–716.0 (n=20) |
| s1d1 | output | 1350.0 / 67.5 / 96.4 / 2.0–256.0 (n=20) |
| s1d1 | cache_read | 5465.0 / 273.2 / 219.2 / 0.0–667.0 (n=20) |
| s1d1 | cache_write | inconnu (0) |
| s1d1 | reasoning | inconnu (0) |
| s1d1 | decision | inconnu (0) |
| s1d1 | tools | inconnu (0) |
| s1d1 | retry | inconnu (0) |
| s1d1 | elapsed_ms | 15448.4 / 772.4 / 1274.5 / 55.3–3763.5 (n=20) |
| s1d1 | decision_ms | 347.0 / 17.4 / 9.6 / 7.4–43.5 (n=20) |
| s1d1 | retries | 0.0 / 0.0 / 0.0 / 0.0–0.0 (n=20) |
| configurable | input | 7450.0 / 372.5 / 215.1 / 163.0–716.0 (n=20) |
| configurable | output | 492.0 / 24.6 / 22.7 / 2.0–61.0 (n=20) |
| configurable | cache_read | 6471.0 / 323.6 / 195.0 / 93.0–667.0 (n=20) |
| configurable | cache_write | inconnu (0) |
| configurable | reasoning | inconnu (0) |
| configurable | decision | inconnu (0) |
| configurable | tools | inconnu (0) |
| configurable | retry | inconnu (0) |
| configurable | elapsed_ms | 31892.8 / 1594.6 / 869.2 / 1173.4–5149.4 (n=20) |
| configurable | decision_ms | 25330.0 / 1266.5 / 324.8 / 1089.2–2238.7 (n=20) |
| configurable | retries | 0.0 / 0.0 / 0.0 / 0.0–0.0 (n=20) |

Reçus gateway : default 36, s1d1 32, configurable 36 ; ces nombres sont des appels, pas des parcours. Les 22 reçus configurable avec `decision_usage` totalisent **8 626 input / 726 output** Jev. 14 reçus n’ont pas de decision_usage : absence ne signifie pas zéro décision facturable. Ces tokens sont séparés de l’usage modèle local ci-dessus.

Tarifs locaux, énergie et facture Jev inconnus ; valeur équivalente et repricing non mesurés, et non nuls. Aucun gain économique revendiqué. Pas de réchauffement/reset forcé ; le cache et le matériel sont partagés et les répétitions ne sont pas indépendantes.

## Paires par cas et répétition

Différence de durée = bras − référence en ms ; les trois résultats et les usages permettent de constater les désaccords, pas de conclure à un gain. Pour chaque paire, les valeurs de durée et tokens portent sur le parcours complet.

| Cas | Rép. | Résultat default / s1d1 / configurable | Durée ms default / s1d1 / configurable | Δ s1d1 / configurable (ms) | Input default / s1d1 / configurable | Output default / s1d1 / configurable |
|---|---:|---|---|---|---|---|
| simple-dev-01 | 0 | pass / pass / pass | 1759.4 / 97.2 / 1288.5 | -1662.2 / -470.9 | 163 / 163 / 163 | 2 / 2 / 2 |
| simple-dev-01 | 1 | pass / pass / pass | 46.7 / 91.8 / 1346.8 | +45.1 / +1300.1 | 163 / 163 / 163 | 2 / 2 / 2 |
| code-dev-01 | 0 | pass / pass / pass | 98.0 / 110.5 / 1366.1 | +12.5 / +1268.1 | 180 / 180 / 180 | 14 / 14 / 14 |
| code-dev-01 | 1 | pass / pass / pass | 94.7 / 113.8 / 1224.0 | +19.1 / +1129.3 | 180 / 180 / 180 | 14 / 14 / 14 |
| diagnostic-dev-01 | 0 | fail / fail / fail | 421.5 / 413.3 / 1548.9 | -8.2 / +1127.4 | 716 / 708 / 708 | 61 / 57 / 57 |
| diagnostic-dev-01 | 1 | fail / fail / fail | 412.2 / 427.3 / 1585.3 | +15.1 / +1173.1 | 716 / 716 / 716 | 61 / 61 / 61 |
| conversation-dev-01 | 0 | pass / pass / pass | 107.9 / 113.5 / 1266.4 | +5.6 / +1158.4 | 362 / 362 / 362 | 4 / 4 / 4 |
| conversation-dev-01 | 1 | pass / pass / pass | 107.9 / 118.3 / 1300.6 | +10.5 / +1192.8 | 362 / 362 / 362 | 4 / 4 / 4 |
| agents-dev-01 | 0 | erreur:ValueError / fail / erreur:ValueError | 167.4 / 3728.4 / 1403.3 | +3561.0 / +1235.9 | 266 / 230 / 266 | 29 / 256 / 29 |
| agents-dev-01 | 1 | erreur:ValueError / fail / erreur:ValueError | 2653.2 / 1244.0 / 1296.3 | -1409.1 / -1356.9 | 266 / 230 / 266 | 29 / 256 / 29 |
| simple-validation-01 | 0 | pass / pass / pass | 43.6 / 84.4 / 1173.4 | +40.7 / +1129.8 | 164 / 164 / 164 | 3 / 3 / 3 |
| simple-validation-01 | 1 | pass / pass / pass | 43.7 / 55.3 / 1174.9 | +11.6 / +1131.1 | 164 / 164 / 164 | 3 / 3 / 3 |
| code-validation-01 | 0 | pass / pass / pass | 100.1 / 132.6 / 1270.3 | +32.4 / +1170.2 | 181 / 181 / 181 | 15 / 15 / 15 |
| code-validation-01 | 1 | pass / pass / pass | 99.8 / 121.4 / 1229.1 | +21.5 / +1129.3 | 181 / 181 / 181 | 15 / 15 / 15 |
| diagnostic-validation-01 | 0 | fail / fail / fail | 397.5 / 430.3 / 1494.4 | +32.8 / +1096.9 | 708 / 716 / 708 | 57 / 61 / 57 |
| diagnostic-validation-01 | 1 | fail / fail / fail | 442.0 / 418.5 / 1569.9 | -23.5 / +1127.9 | 716 / 708 / 708 | 61 / 57 / 57 |
| conversation-validation-01 | 0 | pass / pass / pass | 128.8 / 126.1 / 1273.4 | -2.7 / +1144.6 | 367 / 367 / 367 | 7 / 7 / 7 |
| conversation-validation-01 | 1 | pass / pass / pass | 131.8 / 123.1 / 1323.3 | -8.7 / +1191.6 | 367 / 367 / 367 | 7 / 7 / 7 |
| agents-validation-01 | 0 | pass / fail / pass | 390.5 / 3763.5 / 5149.4 | +3373.0 / +4758.9 | 622 / 232 / 622 | 56 / 256 / 56 |
| agents-validation-01 | 1 | pass / fail / pass | 386.7 / 3735.2 / 2608.7 | +3348.5 / +2222.0 | 622 / 232 / 622 | 56 / 256 / 56 |

## Dispersion des différences appariées

Chaque delta correspond à un même jeu, cas et répétition ; somme / moyenne / écart-type population / min–max. Une différence de tokens ou de temps ne mesure pas une économie financière.

| Comparaison | Mesure (bras − default) | Statistiques |
|---|---|---|
| s1d1 − default | elapsed_ms | 7415.2 / 370.8 / 1365.2 / -1662.2–3561.0 (n=20) |
| s1d1 − default | decision_ms | 347.0 / 17.3 / 9.6 / 7.4–43.5 (n=20) |
| s1d1 − default | input | -860.0 / -43.0 / 116.2 / -390.0–8.0 (n=20) |
| s1d1 − default | output | 850.0 / 42.5 / 85.7 / -4.0–227.0 (n=20) |
| s1d1 − default | cache_read | -1150.0 / -57.5 / 202.3 / -603.0–229.0 (n=20) |
| configurable − default | elapsed_ms | 23859.6 / 1193.0 / 1074.8 / -1356.9–4758.9 (n=20) |
| configurable − default | decision_ms | 25330.0 / 1266.5 / 324.8 / 1089.2–2238.7 (n=20) |
| configurable − default | input | -16.0 / -0.8 / 2.4 / -8.0–0.0 (n=20) |
| configurable − default | output | -8.0 / -0.4 / 1.2 / -4.0–0.0 (n=20) |
| configurable − default | cache_read | -144.0 / -7.2 / 104.6 / -295.0–265.0 (n=20) |

Usage des 22 décisions Jev connues (par reçu, pas par parcours) : input : 8626.0 / 392.1 / 18.4 / 373.0–426.0 (n=22) ; output : 726.0 / 33.0 / 0.0 / 33.0–33.0 (n=22).

## Limites de lecture

Micro-jeux synthétiques, deux répétitions par cas, pas d’inférence générale ni garantie de qualité. Le prototype ne démontre ni installation ni streaming, annulation, erreurs ou intégration validée dans quatre hôtes. Voir `STUDY.md` pour les budgets et le protocole ; les reçus JSONL conservent les réponses et événements.

## Lecture du critère diagnostic

Le critère figé du runner v2 exige la clé de fixture dans le champ evidence. Les réponses observées y placent la valeur dns. La consigne demande cause et evidence sans préciser ce choix : cette ambiguïté limite la portée de ces échecs et ne démontre pas un diagnostic erroné. Les scores enregistrés ne sont pas corrigés après consultation de validation ; une consigne différente exigerait une nouvelle version du jeu.
