# ABOUTME: The one vocabulary of content classes, each with a spoiler flag.
# ABOUTME: Owned here until issue #14; every other module reads from this table.

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

CONTENT_CLASSES: dict[str, ContentClass] = {entry.name: entry for entry in _CLASSES}


def content_class(name: str) -> ContentClass:
    try:
        return CONTENT_CLASSES[name]
    except KeyError:
        choices = ", ".join(CONTENT_CLASSES)
        raise ValueError(
            f"unknown content class {name!r}; use one of: {choices}"
        ) from None


def is_spoiler(name: str) -> bool:
    return content_class(name).spoiler
