# Revue des 98 variables — version 0.2.0

La version initiale avait transformé trop d’options techniques en « paramètres manquants ». Cette revue corrige le code et le registre, sans masquer les exigences réellement non définies.

Chaque variable a été relue individuellement dans le catalogue. Les 278 propositions qualité, et les 3 contraintes unitaires de positivité extraites de la colonne cohérence, ont une citation et une décision dans `revue_regles.csv` : 153 clauses actives, 3 alertes de revue, 83 clauses nécessitant une précision, 42 clauses différées. Les 83 clauses à préciser correspondent à 92 exigences regroupées (certaines clauses demandent à la fois format et longueur). Ce sont des décisions de revue des sources, pas des compteurs d’anomalies d’une extraction.

## Corrections effectives

| Sujet | Correction |
|---|---|
| Obligatoriété | Fin des attentes génériques `required` sur tous les champs. Les vides restent suivis pour les 98 variables. Obligation uniquement si explicite ; les obligations conditionnelles restent différées. |
| Code Portefeuille et codes internes comparables | Deux précisions : format et longueur ; suppression de la liste autorisée ajoutée sans demande source. |
| Dates | Suppression des années minimum/maximum inventées. Dates calendaires valides contrôlées ; comparaisons aux autres dates différées. |
| Parité | > 0 ; suppression de la borne supérieure et de l’obligatoriété non demandées. Égalité à 1 selon devises différée. |
| Coefficients V036/V037 et nominal V056 | Activation de > 0, expressément demandé dans la colonne cohérence, mais ne nécessitant aucune autre colonne. |
| Libellé dérivé incorporé V075 | Obligation unitaire reprise de la directive V074 « libellé associé obligatoire ». La correspondance des valeurs code/libellé reste différée. |
| Devises V057/V058 | Forme et appartenance à une liste officielle ISO 4217 embarquée localement. |
| Type de stock et autres champs demandant absence de variantes de casse | Détection de variantes entre lignes, même sans casse canonique approuvée. |
| Code Valeur | Aucun ISIN imposé à tous les codes. Revue des candidats de forme ISIN et validation stricte si explicitement configurée. Les formats internes restent à préciser. |
| Caractères parasites | Détection des caractères invisibles (dont espace de largeur nulle), en plus des contrôles classiques. |
| Quantité | Valeur nulle/négative signalée pour revue ; autorisation selon type de position différée. |
| PRICEINFO / Clé FIFO | Pas de liste autorisée, longueur ou format arbitraire ajouté par défaut. Obligations selon contexte et unicité composite différées. |
| Rapport | Résultats des contrôles exécutés distincts des précisions métier. `controles.csv` trace chaque clause source. Alertes de conformité distinguées des alertes pour revue humaine. |

## Précisions réellement nécessaires

| Famille | Nombre d’exigences source |
|---|---:|
| Référentiels / domaines autorisés explicitement demandés | 32 |
| Formats d’identifiants reconnus ou conformes au référentiel | 12 |
| Longueurs conformes au référentiel | 10 |
| Bornes ou seuils de valeurs extrêmes demandés sans valeurs chiffrées | 36 |
| Conventions de signe demandées sans définition | 2 |
| Total | 92 |

Ces précisions concernent 82 variables. Les autres variables ont des contrôles unitaires définis, et peuvent aussi comporter des relations différées. Aucune absence d’anomalie ne permet de valider une exigence non paramétrée.

## Ambiguïtés signalées

Pour Date de fin d’engagement et Date Lancement Inventaire, le texte qualité « non future par rapport à la valorisation » entre en tension avec les textes de cohérence « postérieure » ou « ≥ ». Ces comparaisons sont hors périmètre ; l’ambiguïté est documentée pour la phase suivante. Il ne faut pas choisir une direction arbitrairement.

## Référence publique des devises

SIX, agence officielle de maintenance ISO 4217 : [Global Financial Data Standards](https://www.six-group.com/en/products-services/financial-information/market-reference-data/data-standards.html). List One, publication du 17 septembre 2026, récupérée le 12 octobre 2026. Les valeurs sont embarquées dans `invref.json` ; la version, l’URL et l’empreinte de la source XML sont archivées dans le référentiel. La liste officielle ne constitue pas une politique CNP sur les devises autorisées.
