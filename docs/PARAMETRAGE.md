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
| `pending` | Paramètres en attente, chacun avec motif ; la règle disparaît des attentes quand son paramètre est renseigné |
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

Si l’Audit Interne confirme qu’un paramètre ne s’applique pas, retirer l’entrée correspondante de `pending` **avec un motif de décision consigné dans le journal des versions du référentiel**. Ne pas remplir une liste de valeurs autorisées avec les seules valeurs de l’extraction : cela n’est pas un contrôle référentiel. Les 284 attentes initiales constituent un registre prudent, à affiner par classe d’actifs.

Une obligatoriété dépendant d’une autre colonne ne doit pas être remplacée par `required: true` sur toute la base. Elle reste documentée dans `deferred` jusqu’à l’implémentation de la cohérence intercolonnes. De même, `identifier_format: isin` ne convient pas à un champ mélangeant ISIN et codes internes ; ce cas exige un périmètre homogène ou une règle conditionnelle ultérieure.

## Paramètres globaux

- `decimal_separator` : `,` ou `.`.
- `thousands_separator` : espace, virgule, point ou chaîne vide ; différent du séparateur décimal. Groupement par trois chiffres vérifié.
- `date_formats` : `%Y%m%d`, `%Y-%m-%d`, `%d/%m/%Y`, `%d-%m-%Y`.
- `excel_serial_dates` : numéros de dates autorisés seulement pour cellules numériques Excel et calendrier du classeur.
- `check_order` : contrôle optionnel de l’ordre exact des 98 colonnes.
- `track_distinct` : suivi des valeurs distinctes et de l’unicité ; interdiction de le désactiver tant que des règles d’unicité sont actives.

Les seuils de valeurs extrêmes sont traités comme bornes approuvées. Aucun seuil statistique ne sera calibré arbitrairement sur une extraction. Il n’existe pas encore de référentiel externe avec dates d’effet : choisir localement la configuration applicable à l’arrêté et conserver sa version dans le rapport.
