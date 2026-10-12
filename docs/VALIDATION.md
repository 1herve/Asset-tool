# Validation de l’étape QDD — version 0.2.0

## Périmètre et sources

Cahier des charges « 125 - Asset Database Audit Tool.pdf » et « Catalogue_controles_INVREF.xlsx », au 12 octobre 2026. L’en-tête du modèle en ligne 4 correspond exactement aux 98 variables du catalogue ; le modèle ne contient aucune ligne de données.

Les **98 variables ont été revues individuellement**, avec citation et décision pour chaque proposition qualité. Le fichier `revue_regles.csv` présente la revue des clauses ; `couverture_variables.csv` présente les 98 variables. Les textes originaux restent dans `invref.json`.

## État de validation

| Critère | État |
|---|---|
| GitHub et code documenté | Livrés |
| Revue de chaque variable et chaque proposition qualité | 98 variables, 281 propositions tracées |
| Présence des colonnes et suivi de tous les vides | Implémentés et testés |
| Obligations explicites | Date valorisation, code valeur, devises et libellé dérivé incorporé |
| Types, formats techniques, nombres finis, dates calendaires, caractères parasites | Implémentés et testés |
| Positivité des coefficients d’indexation, du nominal et de la parité | Implémentée et testée, conformément à la source |
| Référentiel de devises standard | Liste ISO 4217 courante versionnée et embarquée |
| Domaines, formats internes, longueurs, seuils et conventions non définis | Moteurs implémentés ; 92 exigences source restent à préciser |
| Validation sur extraction réelle | À réaliser localement avec revue des alertes |
| Comparaisons entre colonnes et obligations conditionnelles | Hors périmètre demandé ; documentées pour la suite |

Le registre de 284 options génériques de la version initiale est remplacé. La version 0.2.0 compte les exigences réellement demandées dans la source, et non toutes les options possibles du programme. Détails et explications : `REVUE.md`.

## Vérification du programme

```bash
python -m unittest discover -s tests -v
```

29 tests, dont 98 sous-cas d’anomalies et la vérification des vides sur les 98 variables. Les nouveaux cas vérifient la couverture de chaque phrase source, l’absence d’attentes inventées, la positivité explicite, les codes devises inconnus mais correctement formés, les variantes de casse, les caractères invisibles, les candidats ISIN, les conventions de signe, les obligations reportées depuis une directive source et la justification des non-applicabilités.

Les tests valident les contrôles implémentés et configurés, sans certifier les règles non paramétrées ni l’ensemble des relations métier. Le fichier fictif valide doit produire 98 colonnes présentes, 0 alerte et une indication séparée du référentiel à préciser. Le fichier fictif erroné doit produire les 7 alertes introduites volontairement.

## Pour clôturer la recette métier

1. Fournir les référentiels, formats, longueurs, seuils et conventions effectivement demandés, ou justifier leur non-applicabilité avec approbateur.
2. Documenter les paramètres approuvés dans une configuration versionnée.
3. Exécuter cette configuration sur une extraction réelle, localement.
4. Revoir les alertes avec l’auditeur et conserver les décisions.

Il n’est pas nécessaire d’inventer une borne absolue pour toutes les dates, une liste fermée pour tous les identifiants ou une obligatoriété pour les champs où le catalogue demande seulement le suivi des vides.

## Limites explicites

Les formules Excel sont signalées sans être exécutées ; des zéros initiaux peuvent avoir été perdus avant l’import des codes numériques. Les dates converties par Excel peuvent perdre le numéro de série original, notamment le jour fictif de 1900. Sous Python 3.10, le caractère NUL peut provoquer une erreur d’import CSV explicite ; les tests de parasites utilisent U+0001, compatible avec toutes les versions annoncées.

La liste de devises est une liste courante au 17 septembre 2026 : une extraction historique nécessite le référentiel applicable à son arrêté. Le référentiel pays n’est pas identifié dans la source ; aucun alpha-2/alpha-3 n’est imposé arbitrairement. Les comparaisons d’arrêtés, montants exposés et suivi persistant de décisions auditeur appartiennent aux prochaines étapes.

## Vérifications locales de la version 0.2.0

Les 29 tests passent. Le fichier fictif erroné produit les 7 alertes prévues. Le fichier valide produit 0 alerte, avec la séparation entre résultats techniques et exigences source à préciser. Le modèle Excel vide produit `NON_EXECUTE`, sans contrôle présenté comme exécuté sur des valeurs. Sur 10 000 lignes fictives, 980 000 cellules ont été vérifiées en 13,22 secondes dans cet environnement de développement. Ce temps n’est pas une estimation pour une extraction de production. Les 7 fichiers de rapport et les 281 clauses de traçabilité ont été vérifiés.

Si une règle connue est désactivée dans une configuration personnalisée, `controles.csv` l’indique (`DESACTIVE_PAR_CONFIGURATION` ou `PARTIEL_PAR_CONFIGURATION`) plutôt que de la présenter comme exécutée.
