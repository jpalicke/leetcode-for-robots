# ABOUTME: Unit tests for the explanation rubric: ranges, ungraded versus zero, totals.
# ABOUTME: Core is approach 4, correctness 4, time 2; the space bonus is separate.

import pytest

from practice.rubric import (
    APPROACH_MAX,
    CORE_MAX,
    CORRECTNESS_MAX,
    SPACE_BONUS_MAX,
    TIME_MAX,
    ExplanationScores,
    RubricError,
    format_scores,
)


def test_rubric_constants_match_the_approved_rubric() -> None:
    assert (APPROACH_MAX, CORRECTNESS_MAX, TIME_MAX) == (4, 4, 2)
    assert CORE_MAX == 10
    assert SPACE_BONUS_MAX == 1


def test_full_marks_with_bonus_are_reported_separately() -> None:
    scores = ExplanationScores(approach=4, correctness=4, time=2, space=1)

    assert scores.core_total == 10
    assert scores.bonus == 1
    assert format_scores(scores) == "10/10 +1 bonus"


def test_missing_space_analysis_is_ungraded_not_a_penalty() -> None:
    scores = ExplanationScores(approach=4, correctness=3, time=2, space=None)

    assert scores.core_total == 9
    assert scores.bonus is None
    assert format_scores(scores) == "9/10"


def test_a_zero_is_a_grade_and_none_is_not() -> None:
    zero = ExplanationScores(approach=0, correctness=0, time=0, space=0)
    ungraded = ExplanationScores(None, None, None, None)

    assert zero.is_ungraded is False
    assert format_scores(zero) == "0/10 +0 bonus"
    assert ungraded.is_ungraded is True
    assert format_scores(ungraded) == "not assessed"


def test_partly_graded_core_names_what_was_not_assessed() -> None:
    scores = ExplanationScores(approach=4, correctness=None, time=2, space=None)

    assert scores.core_total is None
    assert scores.assessed_points == 6
    assert scores.assessed_max == 6
    assert format_scores(scores) == "partial 6/6 (correctness not assessed)"


def test_a_bonus_alone_still_says_the_core_was_not_assessed() -> None:
    scores = ExplanationScores(None, None, None, space=1)

    assert scores.is_ungraded is False
    assert format_scores(scores) == "core not assessed +1 bonus"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("approach", 5),
        ("approach", -1),
        ("correctness", 5),
        ("time", 3),
        ("time", -1),
        ("space", 2),
        ("space", -1),
    ],
)
def test_out_of_range_components_are_rejected_with_a_clear_message(
    field: str, value: int
) -> None:
    kwargs: dict[str, int | None] = {
        "approach": None,
        "correctness": None,
        "time": None,
        "space": None,
    }
    kwargs[field] = value

    with pytest.raises(RubricError) as raised:
        ExplanationScores(**kwargs).validate()

    assert field in str(raised.value)
    assert "0 to" in str(raised.value)


def test_booleans_and_floats_are_not_scores() -> None:
    with pytest.raises(RubricError):
        ExplanationScores(
            approach=True, correctness=None, time=None, space=None
        ).validate()
    with pytest.raises(RubricError):
        ExplanationScores(
            approach=1.5,  # type: ignore[arg-type]
            correctness=None,
            time=None,
            space=None,
        ).validate()


def test_scores_round_trip_through_a_journal_record() -> None:
    scores = ExplanationScores(approach=4, correctness=None, time=0, space=1)

    assert ExplanationScores.from_record(scores.to_fields()) == scores
