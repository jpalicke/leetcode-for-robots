# ABOUTME: Unit tests for the content classification vocabulary and spoiler flags.
# ABOUTME: The vocabulary has one home; these tests pin its members and spoiler rules.

import pytest

from practice.classification import CONTENT_CLASSES, content_class, is_spoiler


def test_vocabulary_names_are_the_agreed_set() -> None:
    assert set(CONTENT_CLASSES) == {
        "teaching_explanation",
        "reference_solution",
        "hint",
        "algorithm_implementation",
        "test_data",
        "statement_summary",
    }


@pytest.mark.parametrize("name", ["reference_solution", "hint"])
def test_solution_bearing_classes_are_spoilers(name: str) -> None:
    assert is_spoiler(name)


@pytest.mark.parametrize("name", ["teaching_explanation", "statement_summary"])
def test_explanatory_classes_are_not_spoilers(name: str) -> None:
    assert not is_spoiler(name)


def test_every_class_has_a_description_and_matches_its_key() -> None:
    for key, entry in CONTENT_CLASSES.items():
        assert entry.name == key
        assert entry.description.strip()


def test_unknown_class_is_rejected_with_the_valid_choices() -> None:
    with pytest.raises(ValueError, match="reference_solution"):
        content_class("solution")
