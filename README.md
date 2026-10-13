# Asset Database Audit Tool

Outil Python local d’audit de la qualité des données des **98 variables INVREF**. Il lit une extraction CSV ou Excel, vérifie sa structure et les valeurs de chaque champ, puis génère un rapport détaillé.

Le périmètre actuel couvre l’**exhaustivité** (présence des colonnes et suivi des valeurs manquantes) et la **conformité** (types, formats et règles unitaires configurées). Les contrôles de cohérence entre colonnes et les comparaisons entre arrêtés sont prévus pour la suite. Les traitements s’exécutent sur votre ordinateur et le fichier source reste intact.

## Installation

Le projet nécessite **Python 3.10 ou supérieur** et fonctionne sous macOS, Windows et Linux. Télécharger le dépôt avec Git :

```bash
git clone https://github.com/1herve/Asset-tool.git
cd Asset-tool
```

Sur macOS ou Linux, créer puis activer un environnement Python dédié :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Sur Windows, utiliser l’invite de commandes :

```bat
py -m venv .venv
.venv\Scripts\activate
```

Une fois l’environnement activé, installer l’outil et ses dépendances :

```bash
python -m pip install -e .
```

## Première démonstration

Le dossier `examples/` contient deux fichiers fictifs : un jeu sans anomalie sur les règles configurées et un jeu comportant des erreurs volontaires.

```bash
python -m asset_audit examples/invref_fictif.csv --output reports/demo
python -m asset_audit examples/invref_anomalies.csv --output reports/demo_anomalies
```

Ouvrir `rapport.html` dans chaque dossier de résultats. Sur macOS :

```bash
open reports/demo/rapport.html
open reports/demo_anomalies/rapport.html
```

Le premier jeu produit **98 colonnes présentes et zéro alerte**, avec le statut `A_COMPLETER`, car certaines règles métier attendent leurs paramètres. Le second produit les **7 alertes** prévues pour la démonstration.

Choisir un nouveau dossier de sortie à chaque lancement : l’outil refuse d’écraser un rapport existant.

## Audit d’une extraction

Placer l’extraction dans un dossier local, par exemple `inputs/`, puis lancer la commande adaptée :

```bash
python -m asset_audit inputs/INVREF.csv --delimiter ";" --output reports/audit_csv
python -m asset_audit inputs/INVREF.xlsx --sheet "INVREF" --output reports/audit_excel
```

Si l’en-tête se trouve en ligne 4, ajouter `--header-row 4`. Pour le modèle fourni :

```bash
python -m asset_audit inputs/Catalogue_controles_INVREF.xlsx --sheet "Données INVREF" --header-row 4 --output reports/modele
```

Le modèle sans lignes de données produit `NON_EXECUTE`. Les formats pris en charge sont `.csv` et `.xlsx` ; convertir localement les anciens `.xls`.

| Option | Utilité | Valeur par défaut |
|---|---|---|
| `--output` | Dossier de résultats à créer | `reports/audit` |
| `--config` | Référentiel JSON à appliquer | Référentiel INVREF du projet |
| `--sheet` | Onglet Excel à analyser | Unique onglet du fichier |
| `--header-row` | Ligne de l’en-tête | `1` |
| `--delimiter` | Séparateur CSV | `;` |
| `--encoding` | Encodage CSV | UTF-8 avec ou sans BOM |

L’option `--sheet` est nécessaire lorsqu’un fichier Excel comporte plusieurs onglets. Pour un CSV Windows-1252, ajouter `--encoding cp1252`.

## Contrôles disponibles

Le moteur vérifie les 98 colonnes attendues, les en-têtes vides ou dupliqués, les colonnes inconnues et les lignes dont le nombre de cellules diffère de l’en-tête. L’ordre des colonnes peut être contrôlé si l’option correspondante est activée.

Pour chaque variable, il calcule le nombre de valeurs renseignées et vides, le taux de vide et, si le suivi est activé, le nombre de valeurs distinctes. Il contrôle aussi le type de donnée, les espaces parasites et les caractères invisibles ou de contrôle.

Les règles unitaires définies comprennent notamment :

- Les obligations de renseignement de la date de valorisation, du code valeur, des deux devises et du libellé de l’indicateur de dérivé incorporé.
- La validité des nombres, des séparateurs et des groupements de milliers, ainsi que l’exclusion des nombres infinis ou `NaN`.
- La validité calendaire des dates, y compris les années bissextiles, et le signalement de plusieurs dates de valorisation dans une extraction.
- Le format et l’appartenance des devises à la liste ISO 4217 publiée par SIX le 17 septembre 2026, embarquée localement. Cette liste ne définit pas les devises autorisées dans les portefeuilles CNP.
- La stricte positivité des coefficients d’indexation, du nominal unitaire et de la parité de change.

Le moteur applique les listes autorisées, les formats, les longueurs, les bornes et les conventions de signe lorsqu’ils sont renseignés dans la configuration. Le contrôle strict de la structure et de la clé ISIN peut être activé pour les champs concernés.

Certaines valeurs, comme une quantité nulle ou négative, une duration négative, une convexité négative ou un code ressemblant à un ISIN invalide, déclenchent une **alerte de revue humaine**. Leur interprétation dépend du contexte métier.

## Paramétrage métier et avancement

Les **98 variables ont été revues individuellement** à partir du catalogue. `asset_audit/invref.json` conserve les textes sources, les paramètres, les décisions de revue et les contrôles différés.

Il reste **92 exigences à préciser sur 82 variables** :

| Précision attendue | Nombre |
|---|---:|
| Listes de codes ou référentiels autorisés | 32 |
| Formats d’identifiants | 12 |
| Longueurs d’identifiants | 10 |
| Bornes ou seuils de valeurs atypiques | 36 |
| Conventions de signe | 2 |
| **Total** | **92** |

Le moteur dispose des contrôles correspondants. Leur application complète nécessite les valeurs approuvées par le métier, ou une non-applicabilité justifiée avec un approbateur identifié. Une exigence de longueur est comptée une seule fois, même si elle utilise un minimum et un maximum.

Les correspondances code/libellé, les obligations conditionnelles, les relations entre montants, l’unicité composite et les comparaisons de dates entre colonnes restent à développer dans la phase de cohérence intercolonnes. La recette sur une extraction réelle et les mesures de performance sur les volumes de production restent à réaliser.

## Résultats et rapports

Le rapport distingue les résultats des contrôles exécutés, les alertes de revue humaine et les précisions métier attendues. Zéro anomalie porte uniquement sur les règles exécutées.

| Statut global | Signification |
|---|---|
| `CONFORME_CONTROLES_EXECUTES` | Aucune alerte et aucune exigence unitaire en attente dans la configuration utilisée |
| `A_COMPLETER` | Aucune alerte, mais des règles métier restent à paramétrer |
| `ANOMALIES` | Des anomalies ou alertes de revue ont été relevées ; le détail précise leur nature |
| `NON_EXECUTE` | Aucune ligne de données à contrôler |

Chaque audit terminé produit sept fichiers :

| Fichier | Contenu |
|---|---|
| `rapport.html` | Synthèse à ouvrir dans un navigateur et tableau des 98 variables |
| `anomalies.csv` | Alertes : ligne source, variable, règle, criticité, valeur, seuil et explication |
| `variables.csv` | Statistiques et état des contrôles pour chaque variable |
| `controles.csv` | Traçabilité entre les clauses du catalogue et leur état d’exécution |
| `donnees_normalisees.csv` | Valeurs interprétées par le moteur, avec leur ligne source |
| `synthese.json` | Résultats, paramètres d’import, date d’exécution et empreintes des fichiers |
| `parametres.json` | Copie exacte du référentiel utilisé |

Les valeurs absentes ou illisibles apparaissent vides dans les données normalisées, à lire avec les anomalies. Les formules Excel sont signalées sans être exécutées. Un code stocké comme nombre dans Excel est soumis à revue, car ses zéros initiaux peuvent avoir été perdus avant l’import. Les CSV produits protègent les valeurs susceptibles d’être interprétées comme formules à leur ouverture dans Excel.

Les codes de sortie de la commande sont `0` pour un résultat conforme sur ce périmètre, `1` en présence d’alertes, `2` pour un audit sans alerte dont le statut reste à compléter ou non exécuté, et `3` pour une erreur d’entrée ou de configuration.

## Organisation du projet

| Emplacement | Rôle |
|---|---|
| `asset_audit/engine.py` | Lecture et contrôles des données |
| `asset_audit/__main__.py` | Commande d’exécution et génération des rapports |
| `asset_audit/invref.json` | Référentiel des variables et paramétrage des règles |
| `asset_audit/__init__.py` | Version du programme |
| `tests/test_audit.py` | Tests automatisés |
| `examples/` | Données fictives de démonstration |
| `docs/` | Documentation et matrices de suivi |
| `.github/workflows/tests.yml` | Tests automatiques sur GitHub |
| `pyproject.toml` | Installation du projet et dépendances |

Le [guide de lecture du code](docs/LECTURE_CODE.md) explique les fichiers et les rubriques du JSON. Le [guide de paramétrage](docs/PARAMETRAGE.md) décrit comment renseigner les règles. La [matrice des variables](docs/couverture_variables.csv), la [revue des clauses](docs/revue_regles.csv) et le [document de validation](docs/VALIDATION.md) détaillent la couverture et les étapes de recette.

## Vérification du programme

```bash
python -m unittest discover -s tests -v
```

La suite comprend **29 tests**, avec des sous-cas couvrant les 98 variables. Elle vérifie les formats, les règles configurables, les cas d’erreur, la traçabilité et la production des rapports. GitHub Actions exécute aussi ces tests avec Python 3.10 et 3.12 lors des envois de code et des demandes de fusion.

Ces essais utilisent des données fictives. La validation métier complète nécessite des paramètres approuvés et une recette sur une extraction réelle.

## Conventions de lecture et données locales

Les nombres textuels utilisent par défaut la virgule décimale et l’espace de milliers. Les cellules Excel déjà numériques sont lues comme telles. Les dates acceptées par défaut sont `AAAAMMJJ`, les dates ISO et les dates Excel. Les textes `NULL`, `N/A` et `NaN` sont considérés comme présents, puis vérifiés selon le type du champ.

Le dépôt contient le code, les règles et les exemples fictifs. Les dossiers `inputs/`, `data/` et `reports/` sont exclus du suivi Git pour conserver les extractions réelles et les résultats localement.

Le moteur lit les lignes progressivement. Le suivi des valeurs distinctes et des variantes de casse utilise une mémoire proportionnelle au nombre de valeurs distinctes. `track_distinct: false` réduit ce suivi, à condition de désactiver les règles d’unicité et de nombre maximal de valeurs distinctes. Pour une extraction historique, choisir un référentiel de devises adapté à la date de l’arrêté.
