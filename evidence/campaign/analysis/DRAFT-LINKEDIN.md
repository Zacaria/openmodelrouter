# Brouillon LinkedIn — non publié

J’ai testé un prototype de routage de modèles sur une petite campagne locale : 60 parcours synthétiques, trois approches, cinq familles de tâches, deux répétitions et deux jeux séparés.

La référence était un modèle Qwen local observé dans Hermes, pas le modèle par défaut de ChatGPT. J’ai comparé cette route fixe à s1d1 et à un décideur Jev. Sur ces tâches, le routage n’a pas démontré de gain de réussite.

Le test a aussi révélé une ambiguïté du protocole : le champ « evidence » devait contenir une clé de fixture, mais les modèles y ont mis la cause trouvée. Les diagnostics restent notés en échec selon le critère fixé avant les essais ; ce score ne suffit pas à dire que leurs diagnostics étaient faux. Certains parcours de délégation ont également échoué.

Le plus utile ici n’est pas de promettre une économie : je ne connais ni le coût complet de l’exécution locale ni la facture Jev. Les chiffres ne permettent pas de l’établir. Le code a été testé avec quatre entrées comportementales par parcours ; la délégation était orchestrée par le runner.

C’est un prototype et un résultat borné, pas quatre intégrations hôtes validées ni une conclusion générale. Les plans, reçus et limites accompagnent l’analyse.
