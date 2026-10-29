# ABOUTME: Builds paste-ready, spoiler-aware requests for an existing tutor chat.
# ABOUTME: Content is chosen by class first, then context; nothing is sent or journaled.

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from practice.attempts import MODES
from practice.classification import ALL_CLASSES, is_spoiler
from practice.history import (
    STATUS_LABELS,
    Attempt,
    AttemptView,
    find_attempt,
    load_history,
    view_attempt,
)
from practice.package import ExercisePackage, load_package
from practice.paths import REPO_ROOT, default_package_dir
from practice.tutor_policy import POLICY_PATH, START_PATH

REQUESTS_DIR = "requests"
RECORD_FILE = "readiness.json"
HINT_INDEX = "hints/index.json"
SOLUTION = "solution"
Reveal = int | str | None


class RequestError(Exception):
    """A request cannot be prepared, so nothing is written."""


@dataclass(frozen=True)
class ActionSpec:
    instruction: str  # What the tutor is asked to do.
    needs_code: bool  # Whether the learner's current code path is provided.
    reveal: str  # "hint", "solution" or "none": which reveal option applies.


_PRACTICE_REFRESHER = (
    "The learner wants a refresher on a concept. Ask which concept first. If an "
    "explanation could suggest a solution strategy for this problem, ask the "
    "learner first, and treat their reply as a hint request (TUTOR-004, TUTOR-015)."
)
_STUDY_REFRESHER = (
    "The learner chose study mode for this request. You may teach the concept "
    "openly before the exercise. A full solution is still not authorized "
    "(TUTOR-002)."
)

ACTIONS: dict[str, ActionSpec] = {
    "hint": ActionSpec(
        "The learner asks for a hint. Give exactly one gradual step at the level "
        "below (TUTOR-004), as a question or a nudge, then stop.",
        needs_code=True,
        reveal="hint",
    ),
    "explain-solution": ActionSpec(
        "The learner explicitly asks you to explain the full solution (TUTOR-005). "
        "This does not authorize editing the learner's code (TUTOR-006).",
        needs_code=False,
        reveal=SOLUTION,
    ),
    "review-my-code": ActionSpec(
        "Review the learner's current code with questions and observations. Do not "
        "rewrite it, do not edit the file (TUTOR-006) and do not volunteer a "
        "strategy.",
        needs_code=True,
        reveal="none",
    ),
    "explain-my-approach": ActionSpec(
        "Start an explanation conversation. Invite the learner to explain their "
        "approach, why it works and its time complexity. Grade only what they say "
        "about the submitted code (TUTOR-010). They may defer it without losing "
        "completion.",
        needs_code=True,
        reveal="none",
    ),
    "stuck": ActionSpec(
        "The learner says they are stuck. Open with a gentle check-in: ask what "
        "they tried and what they expected against what they saw. This request "
        "grants no hint; if they want one they will ask for it.",
        needs_code=True,
        reveal="none",
    ),
    "concept-refresher": ActionSpec(
        _PRACTICE_REFRESHER, needs_code=False, reveal="none"
    ),
}

_ASSISTANCE_KINDS = {"explain-solution": "reveal", "concept-refresher": "concept"}


@dataclass(frozen=True)
class Candidate:
    """A piece of problem content, known by its class before it is ever read."""

    label: str  # "statement", "hint" or "notes".
    content_class: str
    path: Path
    level: int | None = None
    names_technique: bool = False


@dataclass(frozen=True)
class PreparedRequest:
    path: Path
    text: str
    notices: list[str]


def parse_reveal(value: str | None) -> Reveal:
    """A hint level such as 2, or the word solution; anything else is refused."""
    if value is None:
        return None
    if value == SOLUTION:
        return SOLUTION
    if value.isdigit():
        return int(value)
    raise RequestError(
        f"--reveal must be a hint level such as 2 or the word {SOLUTION}, not {value!r}"
    )


def prepare_request(
    practice_dir: Path,
    attempt_id: str,
    package_dir: Path | None,
    *,
    action: str,
    mode: str,
    timed: bool,
    reveal: str | None,
) -> PreparedRequest:
    """Build the request and save it. The journal is only ever read."""
    history = load_history(practice_dir)
    attempt = find_attempt(history, attempt_id)
    package = load_package(
        package_dir or default_package_dir(attempt.platform, attempt.problem_id)
    )
    text = build_request(
        practice_dir,
        attempt,
        package,
        action=action,
        mode=mode,
        timed=timed,
        reveal=parse_reveal(reveal),
    )
    path = save_request(practice_dir, attempt.attempt_id, action, text)
    return PreparedRequest(path, text, history.notices)


def save_request(practice_dir: Path, attempt_id: str, action: str, text: str) -> Path:
    """Write the next numbered request file for this attempt; never overwrite."""
    folder = practice_dir / REQUESTS_DIR
    try:
        folder.mkdir(parents=True, exist_ok=True)
        number = _next_number(folder, attempt_id)
        while True:
            path = folder / f"{attempt_id}-{number}-{action}.md"
            try:
                with path.open("x", encoding="utf-8", newline="\n") as handle:
                    handle.write(text)
            except FileExistsError:
                number += 1
                continue
            return path
    except OSError as error:
        raise RequestError(
            f"cannot write the request under {folder}: {error}"
        ) from error


def _next_number(folder: Path, attempt_id: str) -> int:
    pattern = re.compile(rf"^{re.escape(attempt_id)}-(\d+)-")
    used = [
        int(match.group(1))
        for path in folder.iterdir()
        if (match := pattern.match(path.name))
    ]
    return max(used, default=0) + 1


def build_request(
    practice_dir: Path,
    attempt: Attempt,
    package: ExercisePackage,
    *,
    action: str,
    mode: str,
    timed: bool,
    reveal: Reveal,
) -> str:
    spec = ACTIONS.get(action)
    if spec is None:
        raise RequestError(
            f"unsupported action {action!r}; use one of: {', '.join(ACTIONS)}"
        )
    if mode not in MODES:
        raise RequestError(f"unknown mode {mode!r}; use one of: {', '.join(MODES)}")
    if attempt.finished_at is not None:
        raise RequestError(
            f"attempt {attempt.attempt_id} is finished; start a new attempt first"
        )
    _require_matching_ready_package(attempt, package)
    record = _read_record(package.path)

    candidates = _candidates(package.path, record, action)
    target = _check_reveal(action, spec, reveal, attempt, candidates)
    selected = _select(candidates, action, target)

    view = view_attempt(attempt, practice_dir)
    lines = _header(attempt, action, mode, timed)
    lines += _task(spec, action, mode)
    lines += _scope(action, target, selected)
    lines += _context(spec, selected, view)
    lines += _withheld(action, target)
    lines += _after(attempt, action, target)
    return "\n".join(lines) + "\n"


def _require_matching_ready_package(attempt: Attempt, package: ExercisePackage) -> None:
    if (package.platform, package.problem_id) != (attempt.platform, attempt.problem_id):
        raise RequestError(
            f"the package describes {package.platform} {package.problem_id}, "
            f"not {attempt.platform} {attempt.problem_id}"
        )
    if package.suite is None or not package.suite.cases:
        raise RequestError(
            f"the exercise for {attempt.platform} {attempt.problem_id} is not ready: "
            "its package has no test suite yet"
        )


def _read_record(package_dir: Path) -> dict[str, Any]:
    path = package_dir / RECORD_FILE
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RequestError(
            f"the exercise is not ready: cannot read {path}: {error}"
        ) from error
    if not isinstance(record, dict):
        raise RequestError(f"the exercise is not ready: {path} must hold an object")
    blockers = record.get("blockers")
    if blockers:
        raise RequestError(
            "the exercise is not ready, so no request was prepared: "
            + "; ".join(str(blocker) for blocker in blockers)
        )
    return record


def _candidates(
    package_dir: Path, record: dict[str, Any], action: str
) -> list[Candidate]:
    """Every classified piece of content the package offers, none of it read yet."""
    files = record.get("files")
    if not isinstance(files, dict):
        raise RequestError("the exercise is not ready: readiness.json lists no files")
    found: list[Candidate] = []
    for label, key in (("statement", "statement"), ("notes", "notes")):
        entry = files.get(key)
        if isinstance(entry, dict) and "path" in entry and "content_class" in entry:
            content_class = _known_class(str(entry["content_class"]))
            found.append(
                Candidate(label, content_class, _inside(package_dir, entry["path"]))
            )
    if action == "hint":
        found += _hint_candidates(package_dir)
    return found


def _hint_candidates(package_dir: Path) -> list[Candidate]:
    index = package_dir / HINT_INDEX
    try:
        data = json.loads(index.read_text(encoding="utf-8"))
        entries = data["hints"]
        return [
            Candidate(
                "hint",
                _known_class(str(entry["content_class"])),
                _inside(package_dir / "hints", entry["file"]),
                level=int(entry["level"]),
                names_technique=bool(entry["names_technique"]),
            )
            for entry in entries
        ]
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RequestError(
            f"the exercise is not ready: cannot use {index}: {error}"
        ) from error


def _known_class(name: str) -> str:
    if name not in ALL_CLASSES:
        raise RequestError(f"the package uses an unknown content class {name!r}")
    return name


def _inside(folder: Path, relative: object) -> Path:
    path = (folder / str(relative)).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise RequestError(f"{relative!r} points outside the package")
    return path


def _check_reveal(
    action: str,
    spec: ActionSpec,
    reveal: Reveal,
    attempt: Attempt,
    candidates: list[Candidate],
) -> Reveal:
    """The reveal this request is allowed to carry, or an error saying why not."""
    if spec.reveal == "none":
        if reveal is not None:
            raise RequestError(f"--reveal does not apply to {action}")
        return None
    if spec.reveal == SOLUTION:
        if reveal != SOLUTION:
            raise RequestError(
                f"{action} reveals the full solution, so it needs --reveal "
                f"{SOLUTION} to show you asked for it"
            )
        if not any(c.label == "notes" for c in candidates):
            raise RequestError("no classified solution material is available here")
        return SOLUTION
    if reveal == SOLUTION:
        raise RequestError(f"--reveal {SOLUTION} applies only to explain-solution")
    levels = sorted(
        c.level for c in candidates if c.label == "hint" and c.level is not None
    )
    if reveal is None:
        reveal = _next_hint_level(attempt)
        if reveal not in levels:
            raise RequestError(
                "every hint level has already been recorded as given; use --reveal "
                "N to repeat a level or explain-solution to ask for the solution"
            )
    if reveal not in levels:
        raise RequestError(
            f"hint level {reveal} is not classified for this problem; "
            f"available levels: {', '.join(str(level) for level in levels)}"
        )
    return reveal


def _next_hint_level(attempt: Attempt) -> int:
    given = [
        int(event["level"])
        for event in attempt.events
        if event.get("type") == "assistance"
        and event.get("kind") == "hint"
        and event.get("level") is not None
    ]
    return max(given) + 1 if given else 0


def _select(
    candidates: list[Candidate], action: str, target: Reveal
) -> list[Candidate]:
    """Open content, plus exactly what this request's reveal permits. Nothing else."""
    return [
        c
        for c in candidates
        if not is_spoiler(c.content_class) or _permitted(c, action, target)
    ]


def _permitted(candidate: Candidate, action: str, target: Reveal) -> bool:
    if action == "hint":
        return candidate.label == "hint" and candidate.level == target
    if action == "explain-solution":
        return candidate.label == "notes" and target == SOLUTION
    return False


def _display(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _header(attempt: Attempt, action: str, mode: str, timed: bool) -> list[str]:
    timing = (
        "timed (chosen for this request only)"
        if timed
        else "untimed (timing is never carried over from an attempt or request)"
    )
    return [
        f"# Tutor request: {action}",
        "",
        "Paste this whole block into your existing coding-agent tutor chat. It was",
        "prepared locally by `practice request`. Nothing was sent and no agent was",
        "started.",
        "",
        f"Platform: {attempt.platform}",
        f"Problem: {attempt.problem_id}  {attempt.title}",
        f"Attempt: {attempt.attempt_id}",
        f"Mode: {mode}",
        f"Timing: {timing}",
        f"Action: {action}",
        "",
    ]


def _task(spec: ActionSpec, action: str, mode: str) -> list[str]:
    instruction = spec.instruction
    if action == "concept-refresher" and mode == "study":
        instruction = _STUDY_REFRESHER
    return [
        "## Task for the tutor",
        f"Follow {POLICY_PATH} for this whole conversation. If this chat has not "
        f"started a practice session, begin from {START_PATH}.",
        instruction,
        "",
    ]


def _scope(action: str, target: Reveal, selected: list[Candidate]) -> list[str]:
    lines = ["## Permitted reveal scope"]
    if action == "hint":
        hint = next(c for c in selected if c.label == "hint")
        lines.append(f"- Permitted: hint level {target} only. No other level.")
        lines.append(
            "- This level may name the technique, as its hint file says."
            if hint.names_technique
            else "- At this level, do not name the technique."
        )
        lines.append("- A full solution is not authorized.")
    elif action == "explain-solution":
        lines.append(
            "- Permitted: the full solution, for this attempt only. The "
            "authorization ends with this attempt."
        )
    else:
        lines.append(
            "- Nothing beyond the statement: no hint, technique name or full "
            "solution is authorized by this request."
        )
    lines.append("")
    return lines


def _context(
    spec: ActionSpec, selected: list[Candidate], view: AttemptView
) -> list[str]:
    lines = ["## Context provided"]
    for candidate in selected:
        if not is_spoiler(candidate.content_class):
            lines += _open_section(candidate)
        else:
            lines += [
                f"### Permitted {candidate.label} "
                f"({candidate.content_class}, allowed by this request)",
                f"Read only: {_display(candidate.path)}",
                "",
            ]
    if spec.needs_code:
        lines += [
            "### The learner's current code",
            f"Read only this file: {view.code_path}",
            f"Local status: {STATUS_LABELS[view.status]}.",
        ]
        if view.latest_run is not None:
            lines.append(f"Latest local test run: {view.latest_run['status']}.")
        lines.append("")
    return lines


def _open_section(candidate: Candidate) -> list[str]:
    try:
        body = candidate.path.read_text(encoding="utf-8").strip()
    except OSError as error:
        raise RequestError(
            f"the exercise is not ready: cannot read {candidate.path}: {error}"
        ) from error
    return [
        f"### Problem {candidate.label} ({candidate.content_class}, open)",
        body,
        "",
    ]


def _withheld(action: str, target: Reveal) -> list[str]:
    lines = [
        "## Withheld (do not read, quote or reveal)",
        "These content classes are spoilers. None of their content is in this request.",
    ]
    for name, entry in ALL_CLASSES.items():
        if not entry.spoiler:
            continue
        if action == "hint" and name == "hint":
            lines.append(f"- {name}: every level except {target}")
        elif action == "explain-solution" and name == "reference_solution":
            lines.append(f"- {name}: everything except the file named above")
        else:
            lines.append(f"- {name}")
    lines += [
        "Do not open other attempts, earlier attempt files, the package's other "
        "files, `references/` or any other file under `.practice/`, unless the learner "
        "asks.",
        "",
    ]
    return lines


def _after(attempt: Attempt, action: str, target: Reveal) -> list[str]:
    command = f"uv run --locked practice attempt note-assistance {attempt.attempt_id}"
    lines = [
        "## After you help",
        "This request is only preparation. No help has been delivered and nothing "
        "has been recorded. If you actually give help, record it yourself:",
    ]
    if action == "hint":
        lines.append(f"- {command} --kind hint --level {target}")
    elif action in _ASSISTANCE_KINDS:
        lines.append(f"- {command} --kind {_ASSISTANCE_KINDS[action]}")
    else:
        lines.append(
            f"- If you give a hint: {command} --kind hint --level N (the level given)"
        )
    if action == "explain-my-approach":
        lines.append(
            "- Record the assessment: uv run --locked practice attempt explain "
            f"{attempt.attempt_id} --approach N --correctness N --time N "
            "--evidence TEXT --feedback TEXT"
        )
    lines.append("")
    return lines
