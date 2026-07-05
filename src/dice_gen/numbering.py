"""
Standard real-world face-numbering conventions for each die type.

d4 (tetrahedron) has no face-to-face antipodal relationship (its faces are
opposite a *vertex*, not another face), so it has no opposite_sum rule —
values are just assigned once each. All other die types are centrally
symmetric and follow their standard convention:
  d6:  opposite faces sum to 7
  d8:  opposite faces sum to 9
  d10: opposite faces sum to 9 (values 0-9, pairing k with 9-k)
  d12: opposite faces sum to 13
  d20: opposite faces sum to 21
"""

NUMBERING_SCHEMES = {
    "d4": {"values": [1, 2, 3, 4], "opposite_sum": None},
    "d6": {"values": [1, 2, 3, 4, 5, 6], "opposite_sum": 7},
    "d8": {"values": [1, 2, 3, 4, 5, 6, 7, 8], "opposite_sum": 9},
    "d10": {"values": list(range(0, 10)), "opposite_sum": 9},
    "d12": {"values": list(range(1, 13)), "opposite_sum": 13},
    "d20": {"values": list(range(1, 21)), "opposite_sum": 21},
}


def get_values(die_type):
    return list(NUMBERING_SCHEMES[die_type]["values"])


def assign_values_to_opposite_pairs(die_type, face_pairs):
    """
    face_pairs: list of (face_index_a, face_index_b) tuples covering every
    face exactly once. For die types with an opposite_sum rule, each pair is
    assigned (v, opposite_sum - v) so the invariant holds. For d4 (no rule),
    values are just handed out in iteration order — face_pairs there is only
    a convenient grouping, not a real geometric antipodal relationship.

    Returns {face_index: value}.
    """
    scheme = NUMBERING_SCHEMES[die_type]
    values = scheme["values"]
    opposite_sum = scheme["opposite_sum"]

    if opposite_sum is None:
        flat = [face for pair in face_pairs for face in pair]
        return {face: value for face, value in zip(flat, values)}

    remaining = set(values)
    assignment = {}
    for face_a, face_b in face_pairs:
        v_a = min(remaining)
        v_b = opposite_sum - v_a
        if v_b not in remaining:
            raise ValueError(
                f"{die_type}: cannot satisfy opposite_sum={opposite_sum} "
                f"with remaining values {sorted(remaining)}"
            )
        remaining.discard(v_a)
        remaining.discard(v_b)
        assignment[face_a] = v_a
        assignment[face_b] = v_b
    return assignment


def verify_opposite_sum(die_type, face_pairs, assignment):
    opposite_sum = NUMBERING_SCHEMES[die_type]["opposite_sum"]
    if opposite_sum is None:
        return True
    return all(
        assignment[a] + assignment[b] == opposite_sum for a, b in face_pairs
    )
