# Textual Markov

Analyse de sequences d'etiquettes textuelles avec une matrice de transition de Markov.

Le projet part d'un tableau de labels ordonnes par document, calcule les transitions entre categories consecutives, puis genere des sorties par corpus complet ou par partition de metadata, par exemple par decennie.

## Structure

- `src/extraction_rda.csv` : labels sequentiels, avec un document par colonne.
- `src/metadata.tsv` : metadata des documents, avec au moins une colonne `id`.
- `src/transition_matrix.py` : script principal et fonctions d'analyse.
- `src/outputs/` : sorties generees par partition.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Lancer l'analyse

Depuis la racine du projet :

```bash
python3 src/transition_matrix.py
```

Par defaut, le script lit :

- `src/extraction_rda.csv`
- `src/metadata.tsv`

et genere les sorties dans `src/outputs/`, partitionnees par la colonne `decennie`.

## Pour reproduire les résultats de la présentation au colloque Démocratie à l'université

Depuis la racine du projet, apres installation des dependances :

```bash
python3 src/transition_matrix.py \
  --input src/extraction_rda.csv \
  --metadata src/metadata.tsv \
  --partition decennie \
  --filename-col id \
  --output-root src/outputs \
  --length 5 \
  --top-n 5
```

Cette commande regénère les reésultats par décennie dans `src/outputs/`.

## Options utiles

Analyser tout le corpus sans metadata :

```bash
python3 src/transition_matrix.py --no-metadata
```

Changer la partition :

```bash
python3 src/transition_matrix.py --partition annee
```

Changer la longueur des séquences observées et le nombre de résultats :

```bash
python3 src/transition_matrix.py --length 5 --top-n 10
```

Choisir explicitement les chemins :

```bash
python3 src/transition_matrix.py \
  --input src/extraction_rda.csv \
  --metadata src/metadata.tsv \
  --output-root src/outputs
```

## Sorties

Pour chaque partition, le script crée :

- `labels.tsv` : labels transposes, avec un document par ligne.
- `transition_matrix.txt` : probabilites de transition entre categories.
- `top_sequences.txt` : sequences observees les plus frequentes.
- `transition_tree_higlight_weights_curved_labels.png` : graphe des transitions.

## Tests

```bash
python3 -m unittest discover -s tests
```

Les tests couvrent la logique de base : coupe au premier `NaN`, calcul et normalisation des transitions, et comptage des séquences observées.

## References

Dumoulin, H. (2024), "Lire le Désordre des familles avec l'analyse automatique du discours. Une enquête sur l'émergence du genre du rapport", colloque international Effet Foucault, université Paris-I Sorbonne, 13 décembre 2024.

Diwersy, S., Dumoulin, H., Bordes, E., Montrichard, C., Sitri, F. (2026), "La démocratie universitaire vue a travers les comptes rendus de CA : analyse discursive diachronique (1984-2018)", colloque Démocratie a l'universite, Universite d'Orleans.
