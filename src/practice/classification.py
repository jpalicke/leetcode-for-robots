# ABOUTME: The one vocabulary of content classes, each with a spoiler flag.
# ABOUTME: Owned here; the sources, the tutor policy and its checks all read this table.

from dataclasses import dataclass


@dataclass(frozen=True)
class ContentClass:
    name: str
    spoiler: bool  # True means hidden in practice mode until assistance allows it.
    description: str


_CLASSES = (
    ContentClass(
        "teaching_explanation",
        False,
        "Prose that explains a concept without solving a specific problem.",
    ),
    ContentClass(
        "reference_solution",
        True,
        "A complete solution to a specific problem.",
    ),
    ContentClass(
        "hint",
        True,
        "A nudge toward a technique for a specific problem.",
    ),
    ContentClass(
        "algorithm_implementation",
        True,
        "A general algorithm or data structure implementation. It can reveal the "
        "intended technique for a problem, so it is hidden like a solution.",
    ),
    ContentClass(
        "test_data",
        True,
        "Test inputs and expected outputs. Expected outputs reveal answers.",
    ),
    ContentClass(
        "statement_summary",
        False,
        "A short summary of a problem statement that links to the original.",
    ),
)

# Classes for the learner's own material. They are not published sources, so a
# preserved reference can never be given one of these classes.
_LEARNER_CLASSES = (
    ContentClass(
        "prior_attempt",
        True,
        "The learner's earlier code. Hidden in a review or retry until asked for.",
    ),
    ContentClass(
        "session_notes",
        True,
        "Recorded notes about an attempt. They can describe an approach or the help "
        "given, so they are summarized as support needs.",
    ),
    ContentClass(
        "recommendation_label",
        True,
        "A label shown with a suggested problem. It must not name a technique.",
    ),
    ContentClass(
        "generated_context",
        True,
        "A request or export built for the tutor. Filtered by class before it is read.",
    ),
)

# Classes a preserved source may carry.
CONTENT_CLASSES: dict[str, ContentClass] = {entry.name: entry for entry in _CLASSES}
LEARNER_CLASSES: dict[str, ContentClass] = {
    entry.name: entry for entry in _LEARNER_CLASSES
}
ALL_CLASSES: dict[str, ContentClass] = {**CONTENT_CLASSES, **LEARNER_CLASSES}


def content_class(name: str) -> ContentClass:
    try:
        return ALL_CLASSES[name]
    except KeyError:
        choices = ", ".join(ALL_CLASSES)
        raise ValueError(
            f"unknown content class {name!r}; use one of: {choices}"
        ) from None


def is_spoiler(name: str) -> bool:
    return content_class(name).spoiler
