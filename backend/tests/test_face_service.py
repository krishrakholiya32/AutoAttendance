import numpy as np

from app.services.face_service import cosine_similarity, match_face


def test_cosine_similarity_identical_vectors():
    v = np.array([1.0, 2.0, 3.0])
    assert abs(cosine_similarity(v, v) - 1.0) < 1e-6


def test_cosine_similarity_orthogonal_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert abs(cosine_similarity(a, b)) < 1e-6


def test_cosine_similarity_opposite_vectors():
    a = np.array([1.0, 0.0])
    b = np.array([-1.0, 0.0])
    assert abs(cosine_similarity(a, b) - (-1.0)) < 1e-6


def test_match_face_above_threshold_returns_best_match():
    probe = np.array([1.0, 0.0])
    gallery = [(1, np.array([1.0, 0.0])), (2, np.array([0.0, 1.0]))]
    result = match_face(probe, gallery)
    assert result is not None
    student_id, score = result
    assert student_id == 1
    assert score > 0.9


def test_match_face_below_threshold_returns_none():
    probe = np.array([1.0, 0.0])
    gallery = [(1, np.array([0.0, 1.0]))]
    assert match_face(probe, gallery) is None


def test_match_face_empty_gallery_returns_none():
    probe = np.array([1.0, 0.0])
    assert match_face(probe, []) is None


def test_match_face_picks_best_of_multiple_candidates():
    probe = np.array([1.0, 0.1])
    gallery = [(1, np.array([0.0, 1.0])), (2, np.array([1.0, 0.0])), (3, np.array([-1.0, 0.0]))]
    student_id, _ = match_face(probe, gallery)
    assert student_id == 2
