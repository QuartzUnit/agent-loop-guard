"""Tests for similarity functions."""

from loop_guard.similarity import (
    args_similarity,
    edit_similarity,
    jaccard_similarity,
    normalized_edit_distance,
    token_jaccard,
)


class TestJaccard:
    def test_identical_sets(self):
        assert jaccard_similarity({1, 2, 3}, {1, 2, 3}) == 1.0

    def test_disjoint_sets(self):
        assert jaccard_similarity({1, 2}, {3, 4}) == 0.0

    def test_partial_overlap(self):
        assert jaccard_similarity({1, 2, 3}, {2, 3, 4}) == 0.5

    def test_empty_sets(self):
        assert jaccard_similarity(set(), set()) == 1.0

    def test_one_empty(self):
        assert jaccard_similarity({1}, set()) == 0.0


class TestTokenJaccard:
    def test_identical_strings(self):
        assert token_jaccard("hello world", "hello world") == 1.0

    def test_similar_strings(self):
        sim = token_jaccard("how to fix python error", "how to fix python error code")
        assert 0.7 < sim < 1.0

    def test_different_strings(self):
        sim = token_jaccard("hello world", "foo bar baz")
        assert sim == 0.0


class TestEditDistance:
    def test_identical(self):
        assert normalized_edit_distance("abc", "abc") == 0.0

    def test_completely_different(self):
        assert normalized_edit_distance("abc", "xyz") == 1.0

    def test_one_char_diff(self):
        dist = normalized_edit_distance("abc", "abd")
        assert 0 < dist < 0.5

    def test_empty_strings(self):
        assert normalized_edit_distance("", "") == 0.0

    def test_one_empty(self):
        assert normalized_edit_distance("abc", "") == 1.0

    def test_symmetry(self):
        d1 = normalized_edit_distance("kitten", "sitting")
        d2 = normalized_edit_distance("sitting", "kitten")
        assert d1 == d2


class TestEditSimilarity:
    def test_identical(self):
        assert edit_similarity("abc", "abc") == 1.0

    def test_similar(self):
        sim = edit_similarity("kitten", "sitting")
        assert 0.3 < sim < 0.8


class TestArgsSimilarity:
    def test_identical_dicts(self):
        assert args_similarity({"a": 1, "b": 2}, {"a": 1, "b": 2}) == 1.0

    def test_similar_dicts(self):
        sim = args_similarity(
            {"query": "how to fix error"},
            {"query": "how to fix error code"},
        )
        assert sim > 0.5

    def test_none_args(self):
        assert args_similarity(None, None) == 1.0

    def test_string_args(self):
        sim = args_similarity("ls -la /home", "ls -la /home/user")
        assert sim > 0.5

    def test_mixed_types(self):
        # str vs None
        sim = args_similarity("hello", None)
        assert sim < 0.5
