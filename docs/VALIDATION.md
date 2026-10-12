# Validation de l’étape QDD

## Sources et analyse

Périmètre établi à partir du cahier des charges « 125 - Asset Database Audit Tool.pdf » et du fichier « Catalogue_controles_INVREF.xlsx » au 12 octobre 2026.

- `Catalogue variables` : 98 lignes, V001 à V098, 7 types logiques regroupés en 5 familles techniques.
- `Données INVREF` : 98 en-têtes, identiques et dans le même ordre que le catalogue ; en-tête ligne 4, zéro ligne de données.
- `Contrôles formats` : mention explicite des listes autorisées, longueurs, bornes et règles calendaires à charger ultérieurement.
- `Règles inter-colonnes` : 20 règles différées ; les comparaisons contenues dans les textes qualité sont également différées et documentées par variable.

La règle « une seule date de valorisation » est un contrôle unitaire entre lignes, donc incluse. Les comparaisons à la date de valorisation dans les autres variables lisent une seconde colonne, donc exclues de cette étape. Les alertes de signe ambigu sont des alertes de revue, pas des interdictions.

## Critères de recette

| Critère | État livré |
|---|---|
| Dépôt accessible et code documenté | Code et automatisation des tests livrés |
| 98 variables analysées, aucune omise | Référentiel et matrice de 98 lignes |
| Exhaustivité colonnes et suivi de tous les vides | Implémentés et testés |
| Formats des nombres, dates, codes et textes | Implémentés et testés |
| Moteurs domaines, longueurs, bornes, seuils et ISIN | Implémentés et testés avec configurations fictives |
| Paramètres métier approuvés sur tous les champs | **À obtenir : 284 paramètres initiaux en attente** |
| Validation sur extraction réelle | **À réaliser localement ; modèle source vide** |
| Cohérence entre colonnes | Hors périmètre demandé |

La validation complète requiert de résoudre chaque attente (valeur fournie ou non-applicabilité justifiée), d’exécuter l’outil sur une extraction réelle et de revoir les anomalies avec l’auditeur. La conformité du code sur les données fictives ne suffit pas à valider les règles métier.

## Tests reproductibles

```bash
python -m unittest discover -s tests -v
```

19 tests, comprenant **98 sous-cas d’anomalies indépendants** et **98 vérifications d’obligatoriété**. Couverture : valeurs valides, vides, schéma absent/dupliqué/inconnu, lignes CSV irrégulières et multiligne, dates invalides et bissextiles, calendriers Excel 1900/1904, formules Excel, NaN/infini, conventions décimales, groupements erronés, bornes, domaines, casse, espaces, ISIN/Luhn, unicité, dates multiples, paramètres invalides, rapport et refus d’écrasement.

## Limites de cette version

Les codes numériques Excel ont déjà pu perdre des zéros initiaux avant l’audit. Les dates déjà converties par Excel/openpyxl peuvent perdre l’information du numéro de série originel (en particulier le jour fictif de 1900). Les formules ne sont pas recalculées. Les fichiers ne sont pas rapprochés entre arrêtés. Les alertes sont toutes initialisées « à analyser » ; le suivi persistant des décisions auditeur fera partie d’une prochaine étape. Le montant exposé n’est pas calculé ici puisqu’il nécessite de lire un autre champ.

## Vérification locale du 12 octobre 2026

Les 19 tests sont passés. Lancement sur le modèle Excel source : 98 colonnes présentes, 0 ligne, statut `NON_EXECUTE`. Un fichier fictif de 10 000 lignes (980 000 cellules) a été contrôlé en 4,48 secondes dans l’environnement de développement, sans anomalie de format. Ce temps n’est pas une estimation du temps de traitement des bases de production. Installation éditable vérifiée localement.

Empreintes des sources analysées :

- `Catalogue_controles_INVREF.xlsx` : `fcce001d5faa1af3eb1f71bcaa7445a483f4da1bff2b1014a2410ecf1899ddd0`.
- `125 - Asset Database Audit Tool.pdf` : `59e2eae2cf328ad88fba546dc32be62ff3ac7b9dd38be49c9ea31fb2fc267105`.
