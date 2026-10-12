# Paramétrer les règles INVREF

Copier `asset_audit/invref.json` vers un fichier **local**, puis le passer à `--config`. Changer sa `version` à chaque évolution métier. La configuration complète utilisée est archivée dans le rapport et son empreinte est calculée.

## Paramètres par variable

| Paramètre | Signification |
|---|---|
| `required` | `true` obligatoire, `false` facultatif validé, `null` non décidé/conditionnel |
| `allowed_values` | Liste de chaînes canoniques autorisées ; `null` si non fournie |
| `pattern` | Expression régulière appliquée à toute la valeur normalisée |
| `min_length`, `max_length` | Longueurs en caractères |
| `minimum`, `maximum` | Bornes numériques, de préférence sous forme de chaînes décimales avec un point |
| `exclusive_minimum` | Exclut la borne inférieure, par exemple parité > 0 |
| `date_min`, `date_max` | Bornes calendaires absolues ISO `AAAA-MM-JJ` |
| `unique` | Unicité **unitaire** ; ne pas activer pour code valeur/transaction sans validation métier |
| `max_distinct` | Nombre maximal de valeurs distinctes normalisées |
| `max_blank_rate` | Taux maximal de vide entre 0 et 1 |
| `case` | `preserve`, `upper`, `lower` ; toute correction de casse est signalée |
| `identifier_format` | `isin` pour structure et clé de contrôle ; `null` si non applicable/non décidé |
| `pending` | Exigences source à préciser : identifiant, citation exacte, options qui permettent de l’appliquer, justification éventuelle |
| `sign_convention` | `positive`, `negative`, `nonnegative`, `nonpositive` ou `any`, uniquement après validation de la convention |
| `detect_case_variants` | Repère des variantes comme `STOCK` / `stock` dans une extraction, sans inventer une casse canonique |
| `auto_isin` | Signale pour revue une clé invalide sur un code de forme ISIN ; ne force pas les codes internes en ISIN |
| `deferred` | Exigences à implémenter dans les prochains périmètres, non exécutées ici |

Exemple **illustratif**, à remplacer par des valeurs approuvées :

```json
{
  "required": true,
  "allowed_values": ["EUR", "USD"],
  "pattern": "[A-Z]{3}",
  "case": "upper"
}
```

Cet extrait ne remplace pas un référentiel complet : modifier la variable concernée dans la liste `fields`, en conservant ses autres attributs et les 98 variables.

Chaque entrée de `pending` correspond à une exigence du catalogue, avec `source_clause`. Les options `parameters` indiquent comment la satisfaire. Par exemple, « longueur conforme au référentiel » n’est comptée qu’une fois, et peut être décrite par `min_length`, `max_length` ou les deux.

Le registre révisé contient **92 exigences source**, au lieu des 284 options génériques initiales. Il ne crée pas une obligatoriété, une liste fermée ou une borne arbitraire pour chaque variable.

Si un contrôle ne s’applique pas au périmètre, renseigner sa `waiver`, plutôt que supprimer silencieusement l’attente :

```json
"waiver": {
  "reason": "Motif métier de non-applicabilité",
  "approved_by": "Nom ou rôle du référent ayant validé"
}
```

Le rapport affichera `NON_APPLICABLE_JUSTIFIE`, sans prétendre avoir exécuté ce contrôle. Une dérogation sans motif ou approbateur est refusée. Les seuils choisis doivent former le profil approuvé pour le champ ; ne pas renseigner une borne arbitraire pour faire disparaître une attente. Les paramètres strictement positifs des coefficients, du nominal et de la parité sont déjà définis par la source ; pour les coefficients et le nominal, les seuils d’extrêmes restent à préciser.

Ne pas fabriquer les listes autorisées à partir des seules valeurs de l’extraction : cela ne contrôle pas leur appartenance à un référentiel indépendant.

Une obligatoriété dépendant d’une autre colonne ne doit pas être remplacée par `required: true` sur toute la base. Elle reste documentée dans `deferred` jusqu’à l’implémentation de la cohérence intercolonnes. De même, `identifier_format: isin` ne convient pas à un champ mélangeant ISIN et codes internes ; ce cas exige un périmètre homogène ou une règle conditionnelle ultérieure.

## Paramètres globaux

- `decimal_separator` : `,` ou `.`.
- `thousands_separator` : espace, virgule, point ou chaîne vide ; différent du séparateur décimal. Groupement par trois chiffres vérifié.
- `date_formats` : `%Y%m%d`, `%Y-%m-%d`, `%d/%m/%Y`, `%d-%m-%Y`.
- `excel_serial_dates` : numéros de dates autorisés seulement pour cellules numériques Excel et calendrier du classeur.
- `check_order` : contrôle optionnel de l’ordre exact des 98 colonnes.
- `track_distinct` : suivi des valeurs distinctes et de l’unicité ; interdiction de le désactiver tant que des règles d’unicité sont actives.

Les seuils de valeurs extrêmes sont traités comme bornes approuvées. Aucun seuil statistique ne sera calibré arbitrairement sur une extraction. Il n’existe pas encore de référentiel externe avec dates d’effet : choisir localement la configuration applicable à l’arrêté et conserver sa version dans le rapport.

## Référence des devises

Les variables V057 et V058 embarquent la liste ISO 4217 courante SIX (publication 2026-09-17, 178 codes distincts), sans accès réseau au lancement. Elle contient devises, fonds et codes spéciaux. Pour des arrêtés historiques ou un périmètre CNP plus restreint, fournir la liste applicable et documenter sa source/date ; ne pas utiliser sans revue une liste courante pour une extraction ancienne. Le référentiel pays n’étant pas identifié dans le catalogue, aucun choix alpha-2/alpha-3 n’a été imposé.
