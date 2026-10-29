# ABOUTME: The explanation rubric: component limits, validation and score text.
# ABOUTME: Core is approach 4, correctness 4, time 2; space is a separate bonus of 1.

from dataclasses import dataclass
from typing import Any

APPROACH_MAX = 4
CORRECTNESS_MAX = 4
TIME_MAX = 2
CORE_MAX = APPROACH_MAX + CORRECTNESS_MAX + TIME_MAX
SPACE_BONUS_MAX = 1

# (field name, journal field, display name, upper limit) for each core component.
CORE_COMPONENTS: tuple[tuple[str, str, str, int], ...] = (
    ("approach", "approach", "approach", APPROACH_MAX),
    ("correctness", "correctness", "correctness", CORRECTNESS_MAX),
    ("time", "time_complexity", "time", TIME_MAX),
)
SPACE_FIELD = "space_complexity"
NOT_ASSESSED = "not assessed"


class RubricError(ValueError):
    """A rubric component is outside its allowed range."""


@dataclass(frozen=True)
class ExplanationScores:
    """Each component is a whole number or None. None means ungraded, never zero."""

    approach: int | None
    correctness: int | None
    time: int | None
    space: int | None

    def validate(self) -> None:
        for name, _, display, limit in CORE_COMPONENTS:
            _check(display, getattr(self, name), limit)
        _check("space", self.space, SPACE_BONUS_MAX)

    @property
    def core_values(self) -> list[tuple[str, int | None, int]]:
        return [
            (display, getattr(self, name), limit)
            for name, _, display, limit in CORE_COMPONENTS
        ]

    @property
    def core_total(self) -> int | None:
        """The score out of 10, or None unless all three core parts were graded."""
        values = [value for _, value, _ in self.core_values]
        if any(value is None for value in values):
            return None
        return sum(value for value in values if value is not None)

    @property
    def assessed_points(self) -> int:
        return sum(value for _, value, _ in self.core_values if value is not None)

    @property
    def assessed_max(self) -> int:
        return sum(limit for _, value, limit in self.core_values if value is not None)

    @property
    def bonus(self) -> int | None:
        return self.space

    @property
    def is_ungraded(self) -> bool:
        return all(value is None for _, value, _ in self.core_values) and (
            self.space is None
        )

    def to_fields(self) -> dict[str, int | None]:
        fields: dict[str, int | None] = {
            journal: getattr(self, name) for name, journal, _, _ in CORE_COMPONENTS
        }
        fields[SPACE_FIELD] = self.space
        return fields

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ExplanationScores":
        """Read scores from a journal record, checking types and ranges."""
        scores = cls(
            approach=record.get("approach"),
            correctness=record.get("correctness"),
            time=record.get("time_complexity"),
            space=record.get(SPACE_FIELD),
        )
        scores.validate()
        return scores


def format_scores(scores: ExplanationScores) -> str:
    """One line such as `9/10 +1 bonus`; ungraded parts are named, never zeroed."""
    bonus = "" if scores.bonus is None else f" +{scores.bonus} bonus"
    total = scores.core_total
    if total is not None:
        return f"{total}/{CORE_MAX}{bonus}"
    missing = [display for display, value, _ in scores.core_values if value is None]
    if len(missing) == len(CORE_COMPONENTS):
        return f"core {NOT_ASSESSED}{bonus}" if bonus else NOT_ASSESSED
    return (
        f"partial {scores.assessed_points}/{scores.assessed_max} "
        f"({', '.join(missing)} {NOT_ASSESSED}){bonus}"
    )


def _check(name: str, value: object, limit: int) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, int):
        raise RubricError(f"{name} must be a whole number from 0 to {limit}")
    if not 0 <= value <= limit:
        raise RubricError(f"{name} must be from 0 to {limit}, got {value}")
