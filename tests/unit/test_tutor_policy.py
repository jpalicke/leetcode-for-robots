# ABOUTME: Unit tests for the tutor policy parsers and the pure text checks.
# ABOUTME: Covers rule IDs, the class list, technique terms, dev rules, Cursor rule.

import pytest

from practice.classification import ALL_CLASSES
from practice.tutor_policy import (
    REQUIRED_RULE_IDS,
    check_cursor_rule,
    check_dev_rules,
    check_policy_text,
    find_technique_terms,
    parse_class_lines,
    parse_rule_ids,
    render_class_lines,
)

POLICY = """# Policy
- **TUTOR-001** First rule.
- **TUTOR-002** Second rule, see TUTOR-001 for context.
Mentioning TUTOR-003 in prose does not define it.
"""


def test_rule_ids_are_read_from_bullet_definitions_only() -> None:
    assert parse_rule_ids(POLICY) == ["TUTOR-001", "TUTOR-002"]


def test_text_with_no_rules_yields_nothing() -> None:
    assert parse_rule_ids("# nothing here\n") == []


def full_policy() -> str:
    rules = "\n".join(f"- **{rule}** Text." for rule in REQUIRED_RULE_IDS)
    block = "\n".join(render_class_lines())
    return (
        f"{rules}\n<!-- practice:content-classes:begin -->\n{block}\n"
        "<!-- practice:content-classes:end -->\n"
    )


def test_a_complete_policy_has_no_problems() -> None:
    assert check_policy_text(full_policy()) == []


def test_missing_rules_are_named() -> None:
    text = full_policy().replace("- **TUTOR-004** Text.\n", "")
    problems = check_policy_text(text)
    assert any("TUTOR-004" in problem and "missing" in problem for problem in problems)


def test_duplicate_rules_are_named() -> None:
    problems = check_policy_text(full_policy() + "- **TUTOR-005** Again.\n")
    assert any(
        "TUTOR-005" in problem and "duplicate" in problem for problem in problems
    )


def test_unknown_rule_ids_are_flagged() -> None:
    problems = check_policy_text(full_policy() + "- **TUTOR-900** Stray.\n")
    assert any("TUTOR-900" in problem and "unknown" in problem for problem in problems)


def test_class_lines_round_trip_the_vocabulary() -> None:
    parsed = parse_class_lines("\n".join(render_class_lines()))
    assert parsed == {
        name: ("spoiler" if c.spoiler else "open") for name, c in ALL_CLASSES.items()
    }


def test_class_list_drifting_from_the_vocabulary_is_reported() -> None:
    text = full_policy().replace("- `hint`: spoiler\n", "- `hint`: open\n")
    text = text.replace("- `test_data`: spoiler\n", "")
    problems = check_policy_text(text)
    assert any("hint" in problem and "spoiler" in problem for problem in problems)
    assert any("test_data" in problem and "missing" in problem for problem in problems)


def test_missing_class_block_is_reported() -> None:
    rules = "\n".join(f"- **{rule}** Text." for rule in REQUIRED_RULE_IDS)
    assert any("content class" in problem for problem in check_policy_text(rules))


@pytest.mark.parametrize(
    "text",
    [
        "Use a Hash Map here.",
        "a two pointers pass",
        "put it on a stack",
        "Binary search!",
    ],
)
def test_technique_terms_are_found_case_insensitively(text: str) -> None:
    assert find_technique_terms(text)


def test_ordinary_words_are_not_techniques() -> None:
    assert find_technique_terms("Set the stackable pointers aside; research it.") == []


def test_dev_rules_that_import_the_policy_are_flagged() -> None:
    problems = check_dev_rules("See @tutor/TUTOR.md\n", full_policy())
    assert any("import" in problem for problem in problems)


def test_dev_rules_naming_the_policy_in_a_code_span_are_fine() -> None:
    assert (
        check_dev_rules("Policy lives in `@tutor/TUTOR.md`, not here.\n", full_policy())
        == []
    )


def test_dev_rules_that_carry_rule_ids_or_copied_lines_are_flagged() -> None:
    assert check_dev_rules("Follow TUTOR-004 always.\n", full_policy())
    copied = (
        "- **TUTOR-001** First rule that is long enough to count as a copied line.\n"
    )
    policy = full_policy() + copied
    assert any("copies" in p for p in check_dev_rules(copied, policy))


GOOD_RULE = "---\nalwaysApply: false\n---\n\nRead `tutor/TUTOR.md` and follow it.\n"


def test_a_pointer_only_cursor_rule_passes() -> None:
    assert check_cursor_rule({"practice-tutor.mdc": GOOD_RULE}, full_policy()) == []


def test_no_cursor_rules_is_fine() -> None:
    assert check_cursor_rule({}, full_policy()) == []


@pytest.mark.parametrize(
    "text, fragment",
    [
        ("---\nalwaysApply: true\n---\nRead `tutor/TUTOR.md`.\n", "alwaysApply"),
        (
            "---\nalwaysApply: false\nglobs: src/**\n---\nRead `tutor/TUTOR.md`.\n",
            "globs",
        ),
        ("---\nalwaysApply: false\n---\nBe nice.\n", "point"),
        (
            "---\nalwaysApply: false\n---\nRead `tutor/TUTOR.md`. TUTOR-004 applies.\n",
            "rule ID",
        ),
    ],
)
def test_cursor_rule_violations(text: str, fragment: str) -> None:
    problems = check_cursor_rule({"practice-tutor.mdc": text}, full_policy())
    assert any(fragment in problem for problem in problems)
