"""
Scorer Tool — Phase 3
Computes frequency, severity aggregation, and signal confidence per cluster.
"""
import json
import logging

logger = logging.getLogger(__name__)

# Severity priority (highest wins during aggregation)
_SEVERITY_RANK = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def _aggregate_severity(atoms: list[dict]) -> str:
    """Return the highest severity from cluster member atoms."""
    best = "P3"
    best_rank = 3
    for atom in atoms:
        sev = atom.get("severity_signal", "P3") or "P3"
        rank = _SEVERITY_RANK.get(sev, 3)
        if rank < best_rank:
            best = sev
            best_rank = rank
    return best


def _collect_evidence(atoms: list[dict], limit: int = 3) -> str:
    """Collect top evidence spans across cluster members (JSON string)."""
    spans = []
    for atom in atoms:
        raw = atom.get("evidence_spans", "[]")
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, list):
                spans.extend(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
    # Deduplicate and take top N
    seen = set()
    unique = []
    for s in spans:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return json.dumps(unique[:limit])


def _collect_review_ids(atoms: list[dict]) -> str:
    """Collect unique review_ids from cluster members (JSON string)."""
    ids = list({atom["review_id"] for atom in atoms})
    return json.dumps(ids)


def _collect_atom_ids(atoms: list[dict]) -> str:
    """Collect atom_ids from cluster members (JSON string)."""
    ids = [atom["atom_id"] for atom in atoms]
    return json.dumps(ids)


def score_clusters(
    clusters: list[dict],
    total_atom_count: int,
    atom_type: str,
) -> list[dict]:
    """
    Enrich clusters with frequency, severity, evidence, and signal confidence.

    Args:
        clusters:         List of cluster dicts with 'atoms' and 'cohesion_score'.
        total_atom_count: Total atoms of this type (for frequency_pct).
        atom_type:        'bug' or 'feature'

    Returns:
        Same clusters list, enriched with scoring fields.
    """
    for cluster in clusters:
        atoms = cluster["atoms"]
        review_ids = {atom["review_id"] for atom in atoms}

        cluster["frequency"] = len(review_ids)
        cluster["frequency_pct"] = round(
            len(review_ids) / total_atom_count * 100, 2
        ) if total_atom_count > 0 else 0.0

        cluster["top_evidence"] = _collect_evidence(atoms)
        cluster["review_ids"] = _collect_review_ids(atoms)
        cluster["atom_ids"] = _collect_atom_ids(atoms)

        # Bug: aggregate severity from member atoms
        if atom_type == "bug":
            cluster["severity"] = _aggregate_severity(atoms)

        # Signal confidence = extraction confidence avg × cohesion
        avg_conf = sum(
            float(a.get("confidence_score", 0.0)) for a in atoms
        ) / len(atoms) if atoms else 0.0
        cohesion = float(cluster.get("cohesion_score", 1.0))
        cluster["signal_confidence"] = float(round(avg_conf * cohesion, 4))

    logger.info(
        "Scored %d %s clusters (total atoms: %d)",
        len(clusters), atom_type, total_atom_count,
    )
    return clusters
