"""
Clusterer Tool — Phase 3
Agglomerative clustering with cosine distance + adaptive cohesion pass.
"""
import json
import logging
from collections import defaultdict

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics.pairwise import cosine_similarity

from config.settings import COSINE_DISTANCE_THRESHOLD

logger = logging.getLogger(__name__)


def _cohesion(embeddings: np.ndarray) -> float:
    """Average pairwise cosine similarity within a cluster."""
    if len(embeddings) < 2:
        return 1.0
    sim_matrix = cosine_similarity(embeddings)
    n = len(sim_matrix)
    # Average of upper triangle (excluding diagonal)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += sim_matrix[i][j]
            count += 1
    return float(total / count) if count > 0 else 1.0


def cluster_atoms(
    atoms: list[dict],
    embeddings: np.ndarray,
    threshold: float = COSINE_DISTANCE_THRESHOLD,
) -> list[dict]:
    """
    Cluster atoms using agglomerative clustering with cosine distance.

    Adaptive pass: clusters with cohesion < 0.60 are split tighter.

    Args:
        atoms:      List of atom dicts (must have atom_id, review_id, title, etc.)
        embeddings: 2D numpy array of shape (len(atoms), dim)
        threshold:  Cosine distance threshold for initial clustering

    Returns:
        List of cluster dicts, each with:
            - atom_indices: list of indices into the atoms list
            - atoms: list of atom dicts in this cluster
            - cohesion_score: float
    """
    n = len(atoms)
    if n == 0:
        return []

    if n == 1:
        return [{
            "atom_indices": [0],
            "atoms": [atoms[0]],
            "cohesion_score": 1.0,
        }]

    # ── Initial clustering ────────────────────────────────────────────
    model = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=threshold,
        metric="cosine",
        linkage="average",
    )
    labels = model.fit_predict(embeddings)

    # Group atoms by cluster label
    groups: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        groups[label].append(idx)

    # ── Adaptive cohesion pass ────────────────────────────────────────
    final_clusters: list[dict] = []

    for label, indices in groups.items():
        cluster_embeddings = embeddings[indices]
        cohesion = _cohesion(cluster_embeddings)

        if cohesion < 0.60 and len(indices) > 2:
            # Too broad — tighten threshold and re-cluster this group
            tighter_threshold = max(threshold - 0.05, 0.10)
            logger.info(
                "Cluster %d cohesion=%.2f < 0.60 (%d atoms) — re-clustering at %.2f",
                label, cohesion, len(indices), tighter_threshold,
            )
            sub_model = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=tighter_threshold,
                metric="cosine",
                linkage="average",
            )
            sub_labels = sub_model.fit_predict(cluster_embeddings)
            sub_groups: dict[int, list[int]] = defaultdict(list)
            for sub_idx, sub_label in enumerate(sub_labels):
                sub_groups[sub_label].append(indices[sub_idx])

            for sub_indices in sub_groups.values():
                sub_embeddings = embeddings[sub_indices]
                sub_cohesion = _cohesion(sub_embeddings)
                final_clusters.append({
                    "atom_indices": sub_indices,
                    "atoms": [atoms[i] for i in sub_indices],
                    "cohesion_score": float(round(sub_cohesion, 4)),
                })
        else:
            final_clusters.append({
                "atom_indices": indices,
                "atoms": [atoms[i] for i in indices],
                "cohesion_score": float(round(cohesion, 4)),
            })

    logger.info(
        "Clustering complete: %d atoms → %d clusters (threshold=%.2f)",
        n, len(final_clusters), threshold,
    )
    return final_clusters
