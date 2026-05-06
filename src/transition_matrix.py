#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 21 11:01:31 2025

@author: hugodumoulin
"""
import re
import pandas as pd
import os
import matplotlib.pyplot as plt
from collections import defaultdict
import heapq
import networkx as nx
import webcolors
from collections import defaultdict, Counter

# import pygraphviz as pgv

import math

# def process_sequence(sequence):
#     # Ajouter "début" au début de la séquence
#     sequence = ['start'] + sequence.tolist()
    
#     # Remplacer None par "fin"
#     # sequence = ['end' if color is None else color for color in sequence]
#     sequence = ['end' if pd.isna(color) else color for color in sequence]
#     return sequence

def process_sequence(sequence):
    # Ajouter "start" au début
    sequence = ['start'] + sequence.tolist()
    
    new_seq = []
    for color in sequence:
        if pd.isna(color):
            new_seq.append('end')
            break  # arrêter dès le premier NaN
        else:
            new_seq.append(color)
    return new_seq


def build_transition_matrix(df):
    sequences = df.apply(process_sequence, axis=1)
    print(sequences)
# Fonction pour construire la matrice de transition d'un modèle de Markov
    transitions = defaultdict(lambda: defaultdict(int))

    # Compter les transitions entre couleurs successives
    for seq in sequences:
        for i in range(len(seq) - 1):
            transitions[seq[i]][seq[i + 1]] += 1
    
    # Normaliser pour obtenir les probabilités de transition
    transition_matrix = {}
    for color_from, transition_dict in transitions.items():
        total_transitions = sum(transition_dict.values()) #le total des transitions à partir d'une couleur
        
        # if total_transitions == 0:
        #         # état terminal (ex: 'end'), on ne normalise pas, pour éviter les nan
        #         transition_matrix[color_from] = {}
        #         continue
        
        transition_matrix[color_from] = {color_to: count / total_transitions
                                        for color_to, count in transition_dict.items()}#normalisation
    
    with open("transition_matrix.txt", "w") as file:
    # Afficher la matrice de transition
        for color_from, transition_dict in transition_matrix.items():
            print(f"From {color_from}:")
            file.write(f"From {color_from}:\n")
            for color_to, prob in transition_dict.items():
                file.write(f"  To {color_to}: {prob:.2f}\n")
                print(f"  To {color_to}: {prob:.2f}")
            
    return transition_matrix

def get_top_observed_sequences(df, start_state, length, n):
    """
    Retourne les n séquences réellement observées les plus fréquentes
    à partir d'un état donné.
    """
    sequences = df.apply(process_sequence, axis=1)

    observed = Counter()

    for seq in sequences:
        for i, state in enumerate(seq):
            if state == start_state:
                observed_seq = tuple(seq[i:i + length])
                observed[observed_seq] += 1

    total = sum(observed.values())

    if total == 0:
        return []

    top_sequences = observed.most_common(n)

    return [
        {
            "sequence": list(seq),
            "count": count,
            "frequency": count / total
        }
        for seq, count in top_sequences
    ]

def get_top_observed_sequences_in_corpus(df, length, n):
    """
    Retourne les n séquences réellement observées les plus fréquentes
    dans tout le corpus, tronquées à length items.
    """
    sequences = df.apply(process_sequence, axis=1)

    observed = Counter(tuple(seq[:length]) for seq in sequences)
    total = sum(observed.values())

    return [
        {
            "sequence": list(seq),
            "count": count,
            "frequency": count / total
        }
        for seq, count in observed.most_common(n)
    ]

    
import math

def circle_layout(G, radius=5):
    nodes = list(G.nodes())
    n = len(nodes)

    pos = {}
    for i, node in enumerate(nodes):
        angle = 2 * math.pi * i / n
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        pos[node] = (x, y)

    return pos


def plot_transition_tree_v_weights_curved_labels(transition_matrix, partition_value, partition):
    G = nx.DiGraph()

    # Construire le graphe
    for u, trans in transition_matrix.items():
        for v, prob in trans.items():
            G.add_edge(u, v, weight=prob)

    # Sortantes dominantes
    most_probable_edges = {
        u: max(trans, key=trans.get)
        for u, trans in transition_matrix.items() if trans
    }

    # Entrantes dominantes
    best_incoming = {}
    for u, v, d in G.edges(data=True):
        w = d['weight']
        if v not in best_incoming or w > best_incoming[v][1]:
            best_incoming[v] = (u, w)

    pos = circle_layout(G, radius=6)

    # --- Épaisseur proportionnelle à la probabilité ---
    weights = [d['weight'] for _, _, d in G.edges(data=True)]
    w_min, w_max = min(weights), max(weights)

    def scale(w, wmin=w_min, wmax=w_max, min_w=0.2, max_w=5):
        if wmax == wmin:
            return (min_w + max_w) / 2
        return min_w + (w - wmin) / (wmax - wmin) * (max_w - min_w)

    edge_colors = []
    edge_widths = []

    for u, v, d in G.edges(data=True):
        lw = scale(d["weight"])
        if v == most_probable_edges.get(u):
            edge_colors.append("red")
            edge_widths.append(max(lw*1.5, 3))
        elif v in best_incoming and u == best_incoming[v][0]:
            edge_colors.append("#8fd3ff")
            edge_widths.append(max(lw*1.5, 3))
        else:
            edge_colors.append("lightgray")
            edge_widths.append(lw)

    plt.figure(figsize=(10, 10))
    ax = plt.gca()
    
    node_size = 1400
    node_radius = math.sqrt(node_size) / 2


    nx.draw_networkx_nodes(G, pos, node_size=node_size,
                           node_color="lightblue", alpha=0.9)

    nx.draw_networkx_edges(
        G, pos,
        edge_color=edge_colors,
        width=edge_widths,
        arrows=True,
        arrowstyle="-|>",
        arrowsize=15,
        connectionstyle="arc3,rad=0.25",
        min_source_margin=node_radius,
        min_target_margin=node_radius
    )


    nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

    # --- Labels sur les arcs courbés, sauf pour les boucles ---
    for u, v, d in G.edges(data=True):
        if d['weight'] <= 0.10:
            continue

        x1, y1 = pos[u]
        x2, y2 = pos[v]

        if u == v:
            # Boucle : placer le label simplement au-dessus du noeud
            xm, ym = x1, y1 + 1  # ajustable selon la taille du noeud
        else:
            # Arête normale : calcul Bézier pour le milieu de l'arc
            r = -0.25  # rad utilisé dans connectionstyle

            # Point de contrôle pour la courbure
            xc = (x1 + x2)/2 + r*(y1 - y2)
            yc = (y1 + y2)/2 + r*(x2 - x1)

            # Point milieu t=0.5
            xm = (1 - 0.5)**2 * x1 + 2*(1 - 0.5)*0.5*xc + 0.5**2*x2
            ym = (1 - 0.5)**2 * y1 + 2*(1 - 0.5)*0.5*yc + 0.5**2*y2

        # Ajouter le label
        ax.text(
            xm, ym,
            f"{d['weight']:.2f}",
            fontsize=8,
            ha='center',
            va='center',
            rotation=0,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.5, pad=1)
        )
    title = "Graphe des transitions (labels > 0.10, épaisseur ∝ probabilité)"
    if partition_value is not None:
        title = f" - {partition} : {partition_value} – " + title
        
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig('transition_tree_higlight_weights_curved_labels.png', format='png')
    plt.show()
    
def normalize_filename(x):
    x = str(x).strip()
    x = os.path.basename(x)
    x = os.path.splitext(x)[0]
    return x


def safe_folder_name(value):
    value = str(value)
    value = re.sub(r"[^\w\-]+", "_", value)
    return value.strip("_")


def run_analysis_on_dataframe(df, output_dir, start_color, start_tree, length, n, partition_value=None, partition=None):
    os.makedirs(output_dir, exist_ok=True)

    old_cwd = os.getcwd()
    os.chdir(output_dir)

    try:
        df = df.T
        df.to_csv("labels.tsv", sep="\t")

        transition_matrix = build_transition_matrix(df)

        with open("top_sequences.txt", "w") as f:
            f.write("Les 10 séquences complètes les plus observées dans le corpus :\n")
        
            top_corpus_sequences = get_top_observed_sequences_in_corpus(
                        df=df,
                        length=length,
                        n=10
                    )
            if not top_corpus_sequences:
                f.write("Aucune séquence observée.\n")
            else:
                for item in top_corpus_sequences:
                    f.write(
                        f"{item['sequence']} "
                        f"| count={item['count']} "
                        f"| freq={item['frequency']:.3f}\n"
                    )
        
            f.write("\n" + "=" * 80 + "\n")
        
            for clef in transition_matrix.keys():
                f.write(f"\nLes {n} séquences réellement observées les plus fréquentes à partir de {clef}:\n")
        
                top_observed_sequences = get_top_observed_sequences(
                    df=df,
                    start_state=clef,
                    length=length,
                    n=n
                )
        
                if not top_observed_sequences:
                    f.write("Aucune séquence observée.\n")
                    continue
        
                for item in top_observed_sequences:
                    f.write(
                        f"{item['sequence']} "
                        f"| count={item['count']} "
                        f"| freq={item['frequency']:.3f}\n"
                    )



        plot_transition_tree_v_weights_curved_labels(transition_matrix, partition_value, partition)

    finally:
        os.chdir(old_cwd)


def main(
    file,
    metadata_file,
    start_color,
    start_tree,
    length,
    n,
    partition,
    filename_col="id",
    output_root="outputs"
):
    os.chdir("./")

    df = pd.read_csv(file, sep=";")
    metadata = pd.read_csv(metadata_file, sep="\t")

    df.columns = [normalize_filename(col) for col in df.columns]
    metadata[filename_col] = metadata[filename_col].apply(normalize_filename)

    os.makedirs(output_root, exist_ok=True)
    
    if metadata_file is None or partition is None:
        output_dir = os.path.join(output_root, "corpus_complet")
    
        run_analysis_on_dataframe(
            df=df,
            output_dir=output_dir,
            start_color=start_color,
            start_tree=start_tree,
            length=length,
            n=n,
            partition_value="corpus_complet", 
            partition=None
        )

        return

    for partition_value, metadata_part in metadata.groupby(partition):
        selected_files = metadata_part[filename_col].astype(str).tolist()

        existing_files = [col for col in df.columns if col in selected_files]
        missing_files = sorted(set(selected_files) - set(df.columns))

        print("\n" + "=" * 80)
        print(f"Partition : {partition_value}")
        print(f"{len(existing_files)} fichiers trouvés dans extraction_rda.csv")

        if missing_files:
            print(f"{len(missing_files)} fichiers absents de extraction_rda.csv :")
            for f in missing_files:
                print(f"  - {f}")

        if not existing_files:
            print(f"Partition ignorée : aucune colonne correspondante.")
            continue

        df_part = df[existing_files]

        output_dir = os.path.join(output_root, safe_folder_name(partition_value))

        run_analysis_on_dataframe(
            df=df_part,
            output_dir=output_dir,
            start_color=start_color,
            start_tree=start_tree,
            length=length,
            n=n, 
            partition_value=partition_value,
            partition=partition
        )

    
# file ="labels_T.csv"
file="extraction_rda.csv"
partition = "decennie"
metadata_file = "metadata.tsv"

start_color = 'start'
start_tree = 'start'
length=5
n=5
main(
    file=file,
    metadata_file=metadata_file,
    start_color=start_color,
    start_tree=start_tree,
    length=length,
    n=n,
    partition=partition,
    filename_col="id",
    output_root="outputs"
)    
    
    