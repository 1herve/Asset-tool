# Asset Database Audit Tool

Outil Python **local** d’audit des **98 variables INVREF** : exhaustivité du schéma et des champs, conformité des formats et des valeurs. Les contrôles de cohérence entre colonnes, de politique d’investissement et de comparaison entre arrêtés appartiennent aux étapes suivantes.

## Installation et première démonstration

Python 3.10 ou supérieur, sur Windows, macOS ou Linux :

```bash
git clone https://github.com/1herve/Asset-tool.git
cd Asset-tool
python -m venv .venv
```

Activer l’environnement sur Windows : `.venv\Scripts\activate`. Sur macOS/Linux : `source .venv/bin/activate`.

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m asset_audit examples/invref_fictif.csv --output reports/demo
```

Ouvrir `reports/demo/rapport.html` dans un navigateur. Ce fichier est autonome et ne contient aucun appel externe.

**Attention au sens du résultat :** le jeu fictif est correct pour les formats connus, mais renvoie `A_COMPLETER` (code retour 2), car les référentiels métier ne sont pas encore fournis. Ce n’est pas une erreur d’installation. Le jeu `examples/invref_anomalies.csv` contient des anomalies volontaires.

## Utilisation sur une extraction locale

```bash
python -m asset_audit inputs/INVREF.csv --delimiter ";" --output reports/arret_octobre
python -m asset_audit inputs/INVREF.xlsx --sheet "INVREF" --output reports/arret_excel
```

Pour l’onglet du modèle fourni, dont l’en-tête est en ligne 4 :

```bash
python -m asset_audit inputs/Catalogue_controles_INVREF.xlsx --sheet "Données INVREF" --header-row 4 --output reports/modele
```

Le modèle initial est vide : il produit `NON_EXECUTE`, jamais un avis de conformité. Choisir un nouveau dossier de sortie à chaque lancement ; l’outil refuse d’écraser un rapport.

Les paramètres `--delimiter`, `--encoding`, `--header-row` et `--sheet` sont explicites. Le séparateur CSV par défaut est `;`, l’encodage UTF-8 avec ou sans BOM. Pour un CSV Windows ancien, utiliser `--encoding cp1252`. `.csv` et `.xlsx` sont pris en charge ; convertir localement les anciens `.xls`.

## Contrôles présents

- Présence des 98 colonnes ; noms dupliqués, colonnes inconnues, en-têtes vides, largeur irrégulière des lignes ; ordre optionnel.
- Pour **chaque variable** : nombre renseigné, nombre vide, taux de vide, format, espaces parasites, caractères de contrôle, valeurs distinctes et statut de contrôle.
- Champs explicitement obligatoires dans le catalogue : date de valorisation, code valeur, devise de gestion et devise portefeuille.
- Nombres finis, séparateurs et groupements vérifiés, montants signés et taux négatifs acceptés tant qu’aucune borne métier ne les interdit.
- Dates calendaires valides, année bissextile ; dates AAAAMMJJ, ISO et dates Excel ; une seule date de valorisation par extraction, avec alerte soumise à justification.
- Forme des devises : trois lettres majuscules ; parité strictement positive. La forme d’une devise ne prouve pas son appartenance à une liste ISO ou interne.
- Contrôles paramétrables : listes autorisées, casse, expression régulière, longueurs, minimum/maximum, bornes de dates, unicité d’un champ, maximum de valeurs distinctes, taux maximal de vide, format et clé ISIN lorsque applicable.
- Alertes de revue pour valeur boursière nulle/négative, duration négative et convexité négative ; leur signe ne constitue pas un rejet automatique d’un instrument.

L’obligatoriété conditionnelle (call, échéance, source de prix, lot…), les couples code/libellé, les signes selon le type d’actif et l’unicité composite restent différés car ils nécessitent le contexte d’autres colonnes. L’outil ne rend pas tous les champs obligatoires arbitrairement, et ne suppose pas que tous les codes valeur sont des ISIN.

## Couverture et paramètres manquants

Le référentiel `asset_audit/invref.json` contient exactement les **98 variables**, avec nom exact, type logique, criticité, règle qualité originale, contrôle de cohérence original, paramètres en attente et éléments différés.

La matrice `docs/couverture_variables.csv` détaille les 98 lignes. **284 paramètres** restent à renseigner dans la version initiale : certains ne s’appliqueront pas à tous les instruments. Aucun de ces paramètres n’a été déduit des seules valeurs observées ni inventé.

Le moteur des contrôles est implémenté ; **la validation métier complète de l’étape n’est pas acquise sans les référentiels et décisions de l’Audit Interne**. Une absence d’anomalies de format n’est pas une validation des règles désactivées. Voir [Paramétrage](docs/PARAMETRAGE.md) et [Validation](docs/VALIDATION.md).

## Rapports et traçabilité

Chaque exécution produit :

| Fichier | Contenu |
|---|---|
| `rapport.html` | Synthèse lisible et tableau des 98 variables |
| `anomalies.csv` | Ligne source, champ, règle, criticité, brut, normalisé, seuil, message, statut de revue |
| `variables.csv` | Statistiques, conformité et paramètres manquants pour tous les champs |
| `donnees_normalisees.csv` | Valeurs interprétées et ligne source ; valeurs absentes/invalides laissées vides, à lire avec les anomalies |
| `synthese.json` | Résultats, décompte des règles, SHA-256 source et configuration, date UTC, paramètres d’import |
| `parametres.json` | Copie exacte du référentiel utilisé |

La source reste intacte. Les codes CSV gardent leurs zéros initiaux. Les codes numériques Excel déclenchent une alerte car des zéros ont pu être perdus avant l’import. Les formules Excel sont signalées et ne sont jamais exécutées. Les valeurs JSON restent exploitables sans transformation d’export ; les CSV neutralisent avec une apostrophe les cellules susceptibles d’être interprétées comme formules par Excel. Les vides sont `None`/texte vide/espaces seuls ; les textes `NaN`, `NULL`, `N/A` restent des valeurs présentes, puis sont contrôlés selon leur type.

Une date CSV numérique courte n’est pas interprétée comme numéro Excel. Les conventions numériques sont explicites : virgule décimale et espace de milliers par défaut ; pas de détection ambiguë. Dans les fichiers Excel, les nombres déjà typés ne dépendent pas du séparateur CSV. Les dates ISO constituent une extension technique documentée au catalogue ; d’autres formats sont activables.

Codes de sortie : `0` aucun contrôle actif en anomalie et aucun paramètre en attente ; `1` alertes ou schéma invalide ; `2` contrôles à compléter ; `3` erreur d’entrée/configuration. Le statut `CONFORME_CONTROLES_EXECUTES` porte uniquement sur ce périmètre et ne constitue jamais une certification de toute la base.

## Données et volumes

Les traitements sont locaux. Le dépôt contient uniquement code, règles et exemples **fictifs** ; aucune extraction réelle n’est requise pour les tests. Conserver les données réelles et rapports hors GitHub (`inputs/`, `data/`, `reports/` sont ignorés). Le dépôt est actuellement public.

Les lignes CSV et Excel sont lues progressivement et les anomalies sont écrites au fil de l’eau. Le suivi exact des valeurs distinctes consomme une mémoire proportionnelle au nombre de valeurs distinctes par champ. `track_distinct: false` réduit cette mémoire, à condition de désactiver explicitement les règles `unique` et `max_distinct` ; ces statistiques deviennent alors nulles. Aucun benchmark de production CNP n’est encore disponible.
