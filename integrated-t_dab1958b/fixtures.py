"""Synthetic development and validation cases from the frozen pilot plan."""

def cases():
    rows = [
        ('S-D1', 'simple', 'dev', ['Calcule 17 × 6. Réponds uniquement par un entier.'], ['102']),
        ('S-V1', 'simple', 'validation', ['Dans « bleu, rouge, bleu, vert, bleu », combien de fois apparaît bleu ? Réponds uniquement par un entier.'], ['3']),
        ('C-D1', 'code', 'dev', ['Écris uniquement une fonction Python def unique_stable(xs) qui retourne une liste sans doublon, conservant le premier emplacement de chaque entier.'], None),
        ('C-V1', 'code', 'validation', ['Écris uniquement une fonction Python def run_lengths(s) qui renvoie une liste de tuples (caractère, nombre) pour chaque groupe consécutif de caractères identiques.'], None),
        ('A-D1', 'diagnostic', 'dev', ["Une application affiche « connexion impossible » depuis ce matin. Aucune autre information n'est disponible. Donne deux causes distinctes possibles et une vérification concrète qui permette de les distinguer ; n'affirme pas de cause certaine."], None),
        ('A-V1', 'diagnostic', 'validation', ["Une page web est lente uniquement pour une personne. Aucun chronométrage n'est disponible. Donne deux causes distinctes possibles et une mesure concrète pour les départager ; n'affirme pas de cause certaine."], None),
        ('T-D1', 'conversation', 'dev', ['Pour toute cette conversation réponds en français et sans utiliser la lettre « e ». Combien font 2 + 2 ?', 'Donne le nombre premier immédiatement supérieur à 10, uniquement en chiffres.'], ['4', '11']),
        ('T-V1', 'conversation', 'validation', ['Pour toute cette conversation réponds uniquement en chiffres, sans espace ni signe. Combien font 3 + 5 ?', 'Calcule le reste de 137 divisé par 12.'], ['8', '5']),
        ('G-D1', 'agents', 'dev', ['Délègue deux tâches indépendantes : A calcule 8 × 7, B trie 4, 1, 3 par ordre croissant. Réponds sur une seule ligne au format A=<résultat>;B=<résultat>.'], None),
        ('G-V1', 'agents', 'validation', ['Délègue deux tâches indépendantes : A calcule 9 + 6, B inverse le mot lac. Réponds sur une seule ligne au format A=<résultat>;B=<résultat>.'], None),
    ]
    return [dict(id=i, family=f, split=s, prompts=p, expected=e) for i, f, s, p, e in rows]
