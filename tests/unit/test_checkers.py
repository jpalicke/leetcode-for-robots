# ABOUTME: Unit tests for the named output checkers, run on real values.
# ABOUTME: Covers exact, any_order, any_of and the Two Sum index checker.

from practice.checkers import CHECKERS, Verdict

TWO_SUM_ARGS: list[object] = [[2, 7, 11, 15], 9]


def judge(name: str, actual: object, expected: object, args: list[object]) -> Verdict:
    return CHECKERS[name].check(actual, expected, args)


def test_exact_accepts_equal_values_and_rejects_different_ones() -> None:
    assert judge("exact", [0, 1], [0, 1], []).kind == "passed"
    assert judge("exact", [1, 0], [0, 1], []).kind == "failed"


def test_exact_does_not_treat_true_as_one() -> None:
    assert judge("exact", True, 1, []).kind == "failed"


def test_any_order_ignores_ordering() -> None:
    assert judge("any_order", [3, 1, 2], [1, 2, 3], []).kind == "passed"
    assert judge("any_order", [1, 2, 2], [1, 2, 3], []).kind == "failed"


def test_any_order_handles_nested_and_mixed_lists_without_crashing() -> None:
    assert judge("any_order", [[2, 1], [1, 2]], [[1, 2], [2, 1]], []).kind == "passed"
    assert judge("any_order", [1, "a"], ["a", 1], []).kind == "passed"


def test_any_order_flags_a_non_list_as_malformed() -> None:
    assert judge("any_order", "abc", [1], []).kind == "malformed"


def test_any_of_accepts_any_listed_answer() -> None:
    options = [[0, 1], [1, 0]]
    assert judge("any_of", [1, 0], options, []).kind == "passed"
    assert judge("any_of", [2, 3], options, []).kind == "failed"


def test_two_sum_indices_accepts_any_valid_pair_in_any_order() -> None:
    assert judge("indices_sum_to_target", [0, 1], None, TWO_SUM_ARGS).kind == "passed"
    assert judge("indices_sum_to_target", [1, 0], None, TWO_SUM_ARGS).kind == "passed"


def test_two_sum_indices_rejects_wrong_reused_and_out_of_range_pairs() -> None:
    assert judge("indices_sum_to_target", [0, 2], None, TWO_SUM_ARGS).kind == "failed"
    assert judge("indices_sum_to_target", [0, 0], None, [[4], 8]).kind == "failed"
    assert judge("indices_sum_to_target", [0, 9], None, TWO_SUM_ARGS).kind == "failed"
    negative = judge("indices_sum_to_target", [-1, 3], None, [[1, 2, 3, 4], 5])
    assert negative.kind == "failed"


def test_two_sum_indices_flags_wrong_shapes_as_malformed() -> None:
    for actual in ("01", [0], [0, 1, 2], [0.0, 1.0], [True, False], None):
        verdict = judge("indices_sum_to_target", actual, None, TWO_SUM_ARGS)
        assert verdict.kind == "malformed", actual
