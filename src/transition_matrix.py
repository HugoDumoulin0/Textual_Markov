#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyse de sequences textuelles avec une matrice de transition de Markov."""

from __future__ import annotations

import argparse
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = PROJECT_DIR / "extraction_rda.csv"
DEFAULT_METADATA = PROJECT_DIR / "metadata.tsv"
DEFAULT_OUTPUT_ROOT = PROJECT_DIR / "outputs"


def process_sequence(sequence, start_state="start", end_state="end"):
    """Ajoute un etat de depart et coupe la sequence au premier NaN."""
    values = [start_state] + sequence.tolist()

    processed = []
    for value in values:
        if pd.isna(value):
            processed.append(end_state)
            break
        processed.append(value)

    return processed


def iter_sequences(df, start_state="start", end_state="end"):
    """Retourne les sequences ligne par ligne depuis un dataframe transpose."""
    return df.apply(
        lambda row: process_sequence(row, start_state=start_state, end_state=end_state),
        axis=1,
    )


def build_transition_counts(df, start_state="start", end_state="end"):
    """Compte les transitions observees entre deux etats consecutifs."""
    transitions = defaultdict(lambda: defaultdict(int))

    for sequence in iter_sequences(df, start_state=start_state, end_state=end_state):
        for current_state, next_state in zip(sequence, sequence[1:]):
            transitions[current_state][next_state] += 1

    return transitions


def normalize_transition_counts(transitions):
    """Normalise les comptes de transition en probabilites."""
    transition_matrix = {}

    for state_from, transition_counts in transitions.items():
        total = sum(transition_counts.values())
        if total == 0:
            transition_matrix[state_from] = {}
            continue

        transition_matrix[state_from] = {
            state_to: count / total for state_to, count in transition_counts.items()
        }

    return transition_matrix


def build_transition_matrix(df, start_state="start", end_state="end"):
    transitions = build_transition_counts(
        df,
        start_state=start_state,
        end_state=end_state,
    )
    return normalize_transition_counts(transitions)


def get_top_observed_sequences(df, start_state, length, n):
    """Retourne les n sequences observees les plus frequentes depuis un etat."""
    observed = Counter()

    for sequence in iter_sequences(df):
        for index, state in enumerate(sequence):
            if state == start_state:
                observed[tuple(sequence[index : index + length])] += 1

    total = sum(observed.values())
    if total == 0:
        return []

    return [
        {"sequence": list(sequence), "count": count, "frequency": count / total}
        for sequence, count in observed.most_common(n)
    ]


def get_top_observed_sequences_in_corpus(df, length, n):
    """Retourne les n prefixes de sequences les plus frequents dans le corpus."""
    observed = Counter(tuple(sequence[:length]) for sequence in iter_sequences(df))
    total = sum(observed.values())

    if total == 0:
        return []

    return [
        {"sequence": list(sequence), "count": count, "frequency": count / total}
        for sequence, count in observed.most_common(n)
    ]


def write_transition_matrix(transition_matrix, output_path):
    with output_path.open("w", encoding="utf-8") as file:
        for state_from, transition_dict in transition_matrix.items():
            file.write(f"From {state_from}:\n")
            for state_to, probability in transition_dict.items():
                file.write(f"  To {state_to}: {probability:.2f}\n")


def write_top_sequences(df, transition_matrix, output_path, length, n):
    with output_path.open("w", encoding="utf-8") as file:
        file.write(
            f"Les 10 sequences observees les plus frequentes dans le corpus "
            f"(longueur {length}) :\n"
        )

        top_corpus_sequences = get_top_observed_sequences_in_corpus(
            df=df,
            length=length,
            n=10,
        )
        if not top_corpus_sequences:
            file.write("Aucune sequence observee.\n")
        else:
            for item in top_corpus_sequences:
                file.write(
                    f"{item['sequence']} "
                    f"| count={item['count']} "
                    f"| freq={item['frequency']:.3f}\n"
                )

        file.write("\n" + "=" * 80 + "\n")

        for state in transition_matrix:
            file.write(
                f"\nLes {n} sequences observees les plus frequentes "
                f"a partir de {state}:\n"
            )

            top_observed_sequences = get_top_observed_sequences(
                df=df,
                start_state=state,
                length=length,
                n=n,
            )

            if not top_observed_sequences:
                file.write("Aucune sequence observee.\n")
                continue

            for item in top_observed_sequences:
                file.write(
                    f"{item['sequence']} "
                    f"| count={item['count']} "
                    f"| freq={item['frequency']:.3f}\n"
                )


def circle_layout(graph, radius=5):
    nodes = list(graph.nodes())
    if not nodes:
        return {}

    return {
        node: (
            radius * math.cos(2 * math.pi * index / len(nodes)),
            radius * math.sin(2 * math.pi * index / len(nodes)),
        )
        for index, node in enumerate(nodes)
    }


def plot_transition_graph(
    transition_matrix,
    output_path,
    partition_value=None,
    partition=None,
    min_label_probability=0.10,
):
    import matplotlib.pyplot as plt
    import networkx as nx

    graph = nx.DiGraph()

    for state_from, transitions in transition_matrix.items():
        for state_to, probability in transitions.items():
            graph.add_edge(state_from, state_to, weight=probability)

    if graph.number_of_edges() == 0:
        return

    most_probable_edges = {
        state_from: max(transitions, key=transitions.get)
        for state_from, transitions in transition_matrix.items()
        if transitions
    }

    best_incoming = {}
    for state_from, state_to, data in graph.edges(data=True):
        weight = data["weight"]
        if state_to not in best_incoming or weight > best_incoming[state_to][1]:
            best_incoming[state_to] = (state_from, weight)

    position = circle_layout(graph, radius=6)
    weights = [data["weight"] for _, _, data in graph.edges(data=True)]
    weight_min = min(weights)
    weight_max = max(weights)

    def scale_width(weight, min_width=0.2, max_width=5):
        if weight_max == weight_min:
            return (min_width + max_width) / 2
        return min_width + (weight - weight_min) / (weight_max - weight_min) * (
            max_width - min_width
        )

    edge_colors = []
    edge_widths = []

    for state_from, state_to, data in graph.edges(data=True):
        line_width = scale_width(data["weight"])
        if state_to == most_probable_edges.get(state_from):
            edge_colors.append("red")
            edge_widths.append(max(line_width * 1.5, 3))
        elif (
            state_to in best_incoming
            and state_from == best_incoming[state_to][0]
        ):
            edge_colors.append("#8fd3ff")
            edge_widths.append(max(line_width * 1.5, 3))
        else:
            edge_colors.append("lightgray")
            edge_widths.append(line_width)

    plt.figure(figsize=(10, 10))
    axis = plt.gca()

    node_size = 1400
    node_radius = math.sqrt(node_size) / 2

    nx.draw_networkx_nodes(
        graph,
        position,
        node_size=node_size,
        node_color="lightblue",
        alpha=0.9,
    )
    nx.draw_networkx_edges(
        graph,
        position,
        edge_color=edge_colors,
        width=edge_widths,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=15,
        connectionstyle="arc3,rad=0.25",
        min_source_margin=node_radius,
        min_target_margin=node_radius,
    )
    nx.draw_networkx_labels(graph, position, font_size=10, font_weight="bold")

    for state_from, state_to, data in graph.edges(data=True):
        if data["weight"] <= min_label_probability:
            continue

        x1, y1 = position[state_from]
        x2, y2 = position[state_to]

        if state_from == state_to:
            x_mid, y_mid = x1, y1 + 1
        else:
            radius = -0.25
            x_control = (x1 + x2) / 2 + radius * (y1 - y2)
            y_control = (y1 + y2) / 2 + radius * (x2 - x1)
            x_mid = 0.25 * x1 + 0.5 * x_control + 0.25 * x2
            y_mid = 0.25 * y1 + 0.5 * y_control + 0.25 * y2

        axis.text(
            x_mid,
            y_mid,
            f"{data['weight']:.2f}",
            fontsize=8,
            ha="center",
            va="center",
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.5, pad=1),
        )

    title = "Graphe des transitions (labels > 0.10, epaisseur proportionnelle)"
    if partition_value is not None:
        title = f"{partition or 'partition'} : {partition_value} - {title}"

    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, format="png")
    plt.close()


def normalize_filename(value):
    value = str(value).strip()
    value = os.path.basename(value)
    return os.path.splitext(value)[0]


def safe_folder_name(value):
    value = str(value)
    value = re.sub(r"[^\w\-]+", "_", value)
    return value.strip("_")


def run_analysis_on_dataframe(
    df,
    output_dir,
    length,
    n,
    partition_value=None,
    partition=None,
    start_state="start",
    end_state="end",
):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    labels = df.T
    labels.to_csv(output_dir / "labels.tsv", sep="\t")

    transition_matrix = build_transition_matrix(
        labels,
        start_state=start_state,
        end_state=end_state,
    )
    write_transition_matrix(transition_matrix, output_dir / "transition_matrix.txt")
    write_top_sequences(
        labels,
        transition_matrix,
        output_dir / "top_sequences.txt",
        length=length,
        n=n,
    )
    plot_transition_graph(
        transition_matrix,
        output_dir / "transition_tree_higlight_weights_curved_labels.png",
        partition_value=partition_value,
        partition=partition,
    )

    return transition_matrix


def load_data(input_file, metadata_file=None, filename_col="id"):
    df = pd.read_csv(input_file, sep=";")
    df.columns = [normalize_filename(column) for column in df.columns]

    if metadata_file is None:
        return df, None

    metadata = pd.read_csv(metadata_file, sep="\t")
    metadata[filename_col] = metadata[filename_col].apply(normalize_filename)
    return df, metadata


def run_analysis(
    input_file=DEFAULT_INPUT,
    metadata_file=DEFAULT_METADATA,
    partition="decennie",
    filename_col="id",
    output_root=DEFAULT_OUTPUT_ROOT,
    length=5,
    n=5,
):
    output_root = Path(output_root)
    df, metadata = load_data(input_file, metadata_file, filename_col=filename_col)
    output_root.mkdir(parents=True, exist_ok=True)

    if metadata is None or partition is None:
        run_analysis_on_dataframe(
            df=df,
            output_dir=output_root / "corpus_complet",
            length=length,
            n=n,
            partition_value="corpus_complet",
            partition=None,
        )
        return

    for partition_value, metadata_part in metadata.groupby(partition):
        selected_files = metadata_part[filename_col].astype(str).tolist()
        existing_files = [column for column in df.columns if column in selected_files]
        missing_files = sorted(set(selected_files) - set(df.columns))

        print("\n" + "=" * 80)
        print(f"Partition : {partition_value}")
        print(f"{len(existing_files)} fichiers trouves dans {Path(input_file).name}")

        if missing_files:
            print(f"{len(missing_files)} fichiers absents de {Path(input_file).name} :")
            for missing_file in missing_files:
                print(f"  - {missing_file}")

        if not existing_files:
            print("Partition ignoree : aucune colonne correspondante.")
            continue

        run_analysis_on_dataframe(
            df=df[existing_files],
            output_dir=output_root / safe_folder_name(partition_value),
            length=length,
            n=n,
            partition_value=partition_value,
            partition=partition,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Construit des matrices de transition de Markov sur des sequences d'etiquettes."
    )
    parser.add_argument("--input", default=DEFAULT_INPUT, type=Path)
    parser.add_argument("--metadata", default=DEFAULT_METADATA, type=Path)
    parser.add_argument("--partition", default="decennie")
    parser.add_argument("--filename-col", default="id")
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT, type=Path)
    parser.add_argument("--length", default=5, type=int)
    parser.add_argument("--top-n", default=5, type=int)
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="Analyse tout le corpus sans partition metadata.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    metadata_file = None if args.no_metadata else args.metadata
    partition = None if args.no_metadata else args.partition

    run_analysis(
        input_file=args.input,
        metadata_file=metadata_file,
        partition=partition,
        filename_col=args.filename_col,
        output_root=args.output_root,
        length=args.length,
        n=args.top_n,
    )


if __name__ == "__main__":
    main()
