import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dice_gen import numbering


def test_get_values_d20_has_20_unique_values_1_through_20():
    values = numbering.get_values("d20")
    assert len(values) == 20
    assert set(values) == set(range(1, 21))


def test_get_values_d10_has_10_unique_values_0_through_9():
    values = numbering.get_values("d10")
    assert len(values) == 10
    assert set(values) == set(range(0, 10))


def test_d6_opposite_faces_sum_to_7():
    face_pairs = [(0, 1), (2, 3), (4, 5)]
    assignment = numbering.assign_values_to_opposite_pairs("d6", face_pairs)
    assert numbering.verify_opposite_sum("d6", face_pairs, assignment)
    assert set(assignment.values()) == {1, 2, 3, 4, 5, 6}


def test_d20_opposite_faces_sum_to_21():
    face_pairs = [(i, i + 10) for i in range(10)]
    assignment = numbering.assign_values_to_opposite_pairs("d20", face_pairs)
    assert numbering.verify_opposite_sum("d20", face_pairs, assignment)
    assert set(assignment.values()) == set(range(1, 21))


def test_d12_opposite_faces_sum_to_13():
    face_pairs = [(i, i + 6) for i in range(6)]
    assignment = numbering.assign_values_to_opposite_pairs("d12", face_pairs)
    assert numbering.verify_opposite_sum("d12", face_pairs, assignment)
    assert set(assignment.values()) == set(range(1, 13))


def test_d10_opposite_faces_sum_to_9():
    face_pairs = [(i, i + 5) for i in range(5)]
    assignment = numbering.assign_values_to_opposite_pairs("d10", face_pairs)
    assert numbering.verify_opposite_sum("d10", face_pairs, assignment)
    assert set(assignment.values()) == set(range(0, 10))


def test_d4_has_no_opposite_sum_rule_but_assigns_all_values_once():
    face_pairs = [(0, 1), (2, 3)]
    assignment = numbering.assign_values_to_opposite_pairs("d4", face_pairs)
    assert set(assignment.values()) == {1, 2, 3, 4}
