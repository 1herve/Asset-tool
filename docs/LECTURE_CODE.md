# Lire le code de l’outil

Cette page explique où se trouvent les grandes parties du programme et comment lire le référentiel `asset_audit/invref.json`.

## Les fichiers principaux

| Fichier | Rôle |
|---|---|
| `asset_audit/engine.py` | Lit le fichier, applique les règles unitaires et produit les résultats de contrôle. |
| `asset_audit/__main__.py` | Définit la commande à lancer, ses options et les fichiers de rapport à écrire. |
| `asset_audit/invref.json` | Décrit les 98 variables, les paramètres de contrôle et les règles tirées du catalogue. |
| `asset_audit/__init__.py` | Déclare la version du paquet Python. |
| `tests/test_audit.py` | Vérifie automatiquement les cas normaux, les anomalies et la production des rapports. |

## Comment lire `engine.py`

Le moteur commence par des fonctions utilitaires. `number` interprète un nombre en respectant les séparateurs configurés. `parse_date` vérifie les dates et traite, si le fichier est un Excel, les numéros de date Excel. `isin_valid` vérifie la forme et la clé d’un ISIN lorsqu’une règle l’active.

`load_config` charge le JSON puis appelle `validate_config`. Cette validation arrête l’exécution si le référentiel est contradictoire, par exemple si une borne minimale dépasse la borne maximale.

`input_rows` lit les lignes d’un CSV ou d’un fichier XLSX. Il garde les en-têtes répétés pour pouvoir les signaler, conserve le numéro de ligne d’origine et repère les formules Excel sans les exécuter.

`audit` est le moteur principal. Il vérifie d’abord les colonnes attendues, puis examine chaque cellule. Il collecte les anomalies et les alertes de revue, calcule les statistiques par variable et distingue le résultat des contrôles exécutés des précisions métier encore attendues. Les résultats sont transmis progressivement à la commande, sans stocker toute l’extraction en mémoire.

## Comment lire `invref.json`

Le fichier suit le format JSON standard. Ce format n’autorise pas les commentaires `//` ou `/* ... */`. Pour garder le référentiel lisible par le programme, son explication se trouve dans cette documentation.

Les premières clés donnent la version du référentiel, le nombre attendu de variables et la source utilisée. `settings` contient les règles générales de lecture, comme les séparateurs numériques, les formats de dates et le suivi des valeurs distinctes.

Chaque objet de `fields` décrit une variable. `id`, `name` et `kind` identifient le champ. `required`, `allowed_values`, `pattern`, les longueurs et les bornes sont des paramètres éventuellement appliqués par le moteur. Une valeur `null` signifie que le paramètre n’est pas défini dans cette configuration.

`source_quality` et `source_coherence` conservent les phrases du catalogue. `rule_review` trace la décision prise pour chaque clause. `pending` décrit les précisions métier explicitement demandées mais absentes, tandis que `deferred` conserve les contrôles qui nécessitent d’autres colonnes ou un contexte supplémentaire. `decisions` documente les choix de revue pour le champ.

Les paramètres `review_negative` et `review_nonpositive` demandent une revue humaine : ils ne rejettent pas automatiquement l’actif. `identifier_format: "isin"` active le contrôle strict ISIN pour le champ concerné. `auto_isin` repère seulement les valeurs qui ressemblent à des ISIN pour revue, sans imposer que tous les codes soient des ISIN.

## Comment lire `__main__.py`

La fonction `main` interprète les options de ligne de commande, charge le référentiel et appelle `audit`. Les résultats sont d’abord écrits dans un dossier temporaire. Le programme vérifie que le fichier source n’a pas changé pendant le contrôle, puis publie le dossier complet en une seule opération. Il refuse d’écraser un rapport existant.

`write_html` produit la page de synthèse. Les autres sorties détaillent les anomalies, les statistiques des variables, les règles examinées, les données normalisées, la configuration et les empreintes des fichiers utilisés. `csv_safe` protège les CSV contre l’interprétation accidentelle de certaines valeurs comme formules lors de leur ouverture dans Excel.

## Comment lire les tests

Chaque méthode `test_...` construit des données fictives, applique un cas particulier et vérifie le résultat attendu. Les tests montrent que le moteur fonctionne sur ces cas ; ils ne définissent pas les règles métier qui manquent au catalogue et ne remplacent pas une recette sur une extraction réelle.
