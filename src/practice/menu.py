# ABOUTME: Shared menu core: derives state and menu items from the journal and packages.
# ABOUTME: Pure logic with no terminal library; both menu front ends read and act here.

import contextlib
import io
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from practice import clock
from practice.attempt_commands import describe_attempt
from practice.catalog import Catalog, CatalogError, Entry, load_catalog
from practice.curriculum import (
    DEFAULT_CURRICULUM_PATH,
    CurriculumError,
    load_curriculum,
)
from practice.exercises import Exercise
from practice.exercises import exercise_status as package_status
from practice.history import (
    STATUS_LABELS,
    Attempt,
    AttemptError,
    History,
    find_attempt,
    latest_unfinished,
    load_history,
    view_attempt,
)
from practice.recommendations import Candidate, Recommendation, build_recommendation
from practice.reviews import (
    ReviewItem,
    ReviewSchedule,
    describe_review,
    load_schedule,
)
from practice.search import search

MAX_RESULTS = 20
NOT_AVAILABLE_YET = "Not available yet."


class MenuError(Exception):
    """A menu choice or screen is invalid, so nothing was done."""


@dataclass(frozen=True)
class CommandResult:
    code: int
    stdout: str
    stderr: str


CommandRunner = Callable[[list[str]], CommandResult]


def capture_command(
    command: Callable[[list[str]], int], argv: list[str]
) -> CommandResult:
    """Run a practice command in this process and keep what it printed."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = command(argv)
        except SystemExit as stop:  # argparse exits instead of returning.
            code = stop.code if isinstance(stop.code, int) else 2
    return CommandResult(code, out.getvalue(), err.getvalue())


@dataclass(frozen=True)
class MenuEnvironment:
    """Where state lives, plus the one way menus act: the practice commands."""

    practice_dir: Path
    catalog_path: Path
    problems_dir: Path
    references: Path
    run: CommandRunner
    curriculum_path: Path = DEFAULT_CURRICULUM_PATH


@dataclass(frozen=True)
class Screen:
    """Which menu is showing. It is all the state a stateless front end needs."""

    kind: str  # "main", "browse", "problem", "attempt", "reviews" or "recommend".
    words: tuple[str, ...] = ()  # browse: the search words; empty lists packages.
    platform: str = ""
    problem_id: str = ""
    attempt_id: str = ""


MAIN = Screen("main")


@dataclass(frozen=True)
class Item:
    key: str
    label: str
    available: bool = True
    reason: str | None = None  # Why it cannot be chosen; set when unavailable.
    problem: tuple[str, str] | None = None
    attempt_id: str | None = None
    confirm: bool = False  # Needs an explicit confirmation before it acts.
    language: str = "python"  # Which language track a review item belongs to.


@dataclass(frozen=True)
class Menu:
    screen: Screen
    title: str
    lines: tuple[str, ...]
    items: tuple[Item, ...]
    notices: tuple[str, ...] = ()


@dataclass(frozen=True)
class StepResult:
    code: int  # 0 when the action ran and succeeded; the command's code otherwise.
    stdout: str
    stderr: str
    next_screen: Screen


def build_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    builders = {
        "main": _main_menu,
        "browse": _browse_menu,
        "problem": _problem_menu,
        "attempt": _attempt_menu,
        "reviews": _reviews_menu,
        "recommend": _recommend_menu,
    }
    builder = builders.get(screen.kind)
    if builder is None:
        raise MenuError(f"unknown menu {screen.kind!r}")
    return builder(env, screen)


def choose(
    env: MenuEnvironment, screen: Screen, number: int, *, confirmed: bool = False
) -> StepResult:
    """Do what item number NUMBER of the menu on SCREEN says, nothing else."""
    menu = build_menu(env, screen)
    if not 1 <= number <= len(menu.items):
        raise MenuError(f"choose a number from 1 to {len(menu.items)}, not {number}")
    item = menu.items[number - 1]
    if not item.available:
        return _refused(item, screen, item.reason or NOT_AVAILABLE_YET)
    if item.confirm and not confirmed:
        return _refused(
            item,
            screen,
            "This reveals the full solution, so it needs your explicit "
            "confirmation (--confirm-reveal in the numbered menu).",
        )
    return _ACTIONS[item.key](env, screen, item)


def exercise_status(env: MenuEnvironment, platform: str, problem_id: str) -> Exercise:
    """Whether a problem has a ready package. Anything else is pending."""
    return package_status(env.problems_dir, env.references, platform, problem_id)


# Menus


def _main_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    history = load_history(env.practice_dir)
    active = latest_unfinished(history, None, None)
    lines = [
        "Free-text chat still works at any time; this menu is a shortcut.",
        "Practice mode and untimed are the defaults.",
    ]
    due = _due_reviews(env)
    if due:
        lines.append(f"{len(due)} review(s) due.")
    if active is None:
        lines.insert(0, "No unfinished attempt.")
        resume = Item(
            "resume", "Resume your active attempt", False, "No unfinished attempt."
        )
    else:
        view = view_attempt(active, env.practice_dir)
        lines.insert(0, f"Active attempt: {active.attempt_id}")
        lines.insert(1, f"  {describe_attempt(active)}  {STATUS_LABELS[view.status]}")
        resume = Item(
            "resume",
            f"Resume your active attempt ({active.problem_id} {active.title})",
            attempt_id=active.attempt_id,
        )
    items = (
        resume,
        Item("browse", "Browse and select a problem"),
        Item("progress", "Progress and notes"),
        Item("reviews", "Review problems that are due"),
        Item("recommendations", "Get a recommendation for what to practice next"),
        Item("study", "Study a concept (study mode)", False, NOT_AVAILABLE_YET),
        Item(
            "timed",
            "Timed practice (optional; always needs your explicit opt-in)",
            False,
            NOT_AVAILABLE_YET,
        ),
    )
    return Menu(screen, "Main menu", tuple(lines), items, tuple(history.notices))


def _browse_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    catalog = _catalog(env)
    query = " ".join(screen.words).strip()
    if query:
        matches = search(catalog, query)
        entries = matches[:MAX_RESULTS]
        title = f"Problems matching {query!r}"
        lines = [f"{len(matches)} match(es)."] if matches else []
        if not matches:
            lines.append(f"No {catalog.platform} problems match {query!r}.")
        if len(matches) > MAX_RESULTS:
            lines.append(f"Showing the first {MAX_RESULTS}. Refine your search.")
    else:
        entries, extras = _packaged_entries(env, catalog)
        title = "Problems with an exercise package"
        lines = list(extras)
    items = [_problem_item(env, entry) for entry in entries]
    items.append(Item("main", "Back to the main menu"))
    return Menu(screen, title, tuple(lines), tuple(items))


def _problem_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    entry = _entry(_catalog(env), screen.platform, screen.problem_id)
    exercise = exercise_status(env, screen.platform, screen.problem_id)
    history = load_history(env.practice_dir)
    lines = [
        f"{entry.frontend_question_id}  {entry.title}  [{_difficulty(entry)}]",
        "Exercise: ready" if exercise.ready else f"Exercise: {exercise.reason}",
        "A new attempt starts in practice mode, untimed, with a blank file.",
    ]
    items: list[Item] = []
    existing = latest_unfinished(history, screen.platform, screen.problem_id)
    if existing is not None and exercise.ready:
        items.append(
            Item(
                "resume-problem",
                f"Resume your unfinished attempt ({existing.attempt_id})",
                attempt_id=existing.attempt_id,
            )
        )
    items.append(
        Item(
            "start",
            "Start a new practice attempt",
            exercise.ready,
            None if exercise.ready else exercise.reason,
            problem=(screen.platform, screen.problem_id),
        )
    )
    items.append(Item("main", "Back to the main menu"))
    return Menu(screen, "Problem", tuple(lines), tuple(items), tuple(history.notices))


def _reviews_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    """Due reviews to start, then upcoming ones for information. No code is shown."""
    schedule = _schedule(env)
    today = clock.today()
    due, upcoming = schedule.due(today), schedule.upcoming(today)
    lines = [f"Reviews as of {today.isoformat()}"]
    if not schedule.items:
        lines.append("No reviews scheduled yet. Pass a problem to schedule one.")
    lines.append("Reviews start from a blank file. Earlier solutions are never shown.")
    if upcoming:
        lines.append("Upcoming:")
        lines.extend(f"  {describe_review(item)}" for item in upcoming)
    items = [_review_item(env, item) for item in due]
    items.append(Item("main", "Back to the main menu"))
    notices = tuple(schedule.notices)
    return Menu(screen, "Reviews due", tuple(lines), tuple(items), notices)


def _recommendation(env: MenuEnvironment) -> Recommendation:
    catalog = _catalog(env)
    try:
        curriculum = load_curriculum(env.curriculum_path, catalog)
        return build_recommendation(
            env.practice_dir,
            catalog,
            curriculum,
            lambda platform, problem_id: (
                exercise_status(env, platform, problem_id).ready
            ),
            clock.today(),
        )
    except (CurriculumError, clock.ClockError) as error:
        raise MenuError(str(error)) from error


def _recommend_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    """The recommendation and its reason, then a way to start it or choose another."""
    result = _recommendation(env)
    if result.primary is None:
        lines = [result.message]
    else:
        lines = ["Recommended next:", *_describe(result.primary)]
        if result.alternatives:
            lines.append("Other options:")
            for candidate in result.alternatives:
                lines.extend(_describe(candidate))
    lines.append("This only suggests. You can start any other problem instead.")
    items = [_recommended_item(c, first) for first, c in _ranked(result)]
    items.append(Item("browse", "Pick another problem: browse and select"))
    items.append(Item("main", "Back to the main menu"))
    return Menu(screen, "Recommendation", tuple(lines), tuple(items))


def _ranked(result: Recommendation) -> list[tuple[bool, Candidate]]:
    return [(number == 0, c) for number, c in enumerate(result.candidates)]


def _describe(candidate: Candidate) -> list[str]:
    return [
        f"  {candidate.problem_id}  {candidate.label}",
        f"    Why: {candidate.reason_phrase}. {candidate.detail}",
        f"    Evidence: {candidate.evidence.text}",
    ]


_VERBS = {"start": "Start", "resume": "Resume", "review": "Start the review of"}
_ITEM_KEYS = {"start": "start", "resume": "review-resume", "review": "review-start"}


def _recommended_item(candidate: Candidate, primary: bool) -> Item:
    verb = _VERBS[candidate.action]
    prefix = "Recommended: " if primary else "Instead: "
    label = f"{prefix}{verb} {candidate.problem_id}  {candidate.label}"
    return Item(
        _ITEM_KEYS[candidate.action],
        label,
        problem=(candidate.platform, candidate.problem_id),
        attempt_id=candidate.attempt_id,
    )


def _review_item(env: MenuEnvironment, review: ReviewItem) -> Item:
    exercise = exercise_status(env, review.platform, review.problem_id)
    name = f"{review.problem_id}  {review.title}  due {review.due_on.isoformat()}"
    problem = (review.platform, review.problem_id)
    if review.open_attempt_id:
        return Item(
            "review-resume",
            f"Resume your review attempt ({name})",
            exercise.ready,
            None if exercise.ready else exercise.reason,
            problem=problem,
            attempt_id=review.open_attempt_id,
            language=review.language,
        )
    return Item(
        "review-start",
        f"Start the review ({name})",
        exercise.ready,
        None if exercise.ready else exercise.reason,
        problem=problem,
        language=review.language,
    )


def _schedule(env: MenuEnvironment) -> ReviewSchedule:
    try:
        return load_schedule(env.practice_dir)
    except clock.ClockError as error:
        raise MenuError(str(error)) from error


def _due_reviews(env: MenuEnvironment) -> list[ReviewItem]:
    return _schedule(env).due(clock.today())


def _attempt_menu(env: MenuEnvironment, screen: Screen) -> Menu:
    history = load_history(env.practice_dir)
    attempt = find_attempt(history, screen.attempt_id)
    view = view_attempt(attempt, env.practice_dir)
    lines = [
        f"Attempt {attempt.attempt_id}",
        f"  {describe_attempt(attempt)}",
        f"  Status: {STATUS_LABELS[view.status]}",
        "Hints and explanations prepare a request; nothing counts as given until "
        "help is actually delivered and recorded.",
    ]
    blocked = _attempt_block(env, attempt)

    def action(key: str, label: str, confirm: bool = False) -> Item:
        return Item(
            key,
            label,
            blocked is None,
            blocked,
            attempt_id=attempt.attempt_id,
            confirm=confirm,
        )

    items = (
        action("test", "Run my tests"),
        action("hint", "Request a hint (one gradual step)"),
        action(
            "explain-approach", "Request an explanation conversation about my approach"
        ),
        action(
            "explain-solution",
            "Request the full solution explanation (a reveal; asks you to confirm)",
            confirm=True,
        ),
        Item("notes", "Show progress and notes", attempt_id=attempt.attempt_id),
        Item("main", "Back to the main menu"),
    )
    return Menu(screen, "Attempt menu", tuple(lines), items, tuple(history.notices))


def _attempt_block(env: MenuEnvironment, attempt: Attempt) -> str | None:
    """Why the attempt cannot be tested or asked about, or None when it can."""
    if attempt.finished_at is not None:
        return "This attempt is finished. Start a new attempt from the problem list."
    exercise = exercise_status(env, attempt.platform, attempt.problem_id)
    return None if exercise.ready else exercise.reason


# Browsing helpers


def _catalog(env: MenuEnvironment) -> Catalog:
    try:
        return load_catalog(env.catalog_path)
    except CatalogError as error:
        raise MenuError(str(error)) from error


def _entry(catalog: Catalog, platform: str, problem_id: str) -> Entry:
    if catalog.platform == platform:
        for entry in catalog.entries:
            if str(entry.frontend_question_id) == problem_id:
                return entry
    raise MenuError(f"{platform} {problem_id} is not in the catalog")


def _difficulty(entry: Entry) -> str:
    return entry.difficulty + (" premium" if entry.paid_only else "")


def _problem_item(env: MenuEnvironment, entry: Entry) -> Item:
    exercise = exercise_status(env, entry.platform, str(entry.frontend_question_id))
    return Item(
        "select",
        f"{entry.frontend_question_id}  {entry.title}  [{_difficulty(entry)}]",
        exercise.ready,
        None if exercise.ready else exercise.reason,
        problem=(entry.platform, str(entry.frontend_question_id)),
    )


def _packaged_entries(
    env: MenuEnvironment, catalog: Catalog
) -> tuple[list[Entry], list[str]]:
    """Catalog entries that have a package folder, in ID order."""
    found: list[Entry] = []
    extras: list[str] = []
    folders = (
        sorted(path.name for path in env.problems_dir.iterdir() if path.is_dir())
        if env.problems_dir.is_dir()
        else []
    )
    for name in folders:
        platform, _, problem_id = name.partition("-")
        try:
            found.append(_entry(catalog, platform, problem_id))
        except MenuError:
            extras.append(f"Skipped {name}: it matches no catalog problem.")
    found.sort(key=lambda entry: entry.frontend_question_id)
    if not found:
        extras.append("No exercise packages found.")
    extras.append("To find any other problem, search the catalog by words.")
    return found, extras


# Actions


def _refused(item: Item, screen: Screen, why: str) -> StepResult:
    text = f"{item.label}: {why} Nothing was done."
    return StepResult(1, text + "\n", "", screen)


def _package_flags(env: MenuEnvironment, platform: str, problem_id: str) -> list[str]:
    return ["--package", str(env.problems_dir / f"{platform}-{problem_id}")]


def _run(
    env: MenuEnvironment, screen: Screen, argv: list[str], next_screen: Screen | None
) -> StepResult:
    result = env.run(argv)
    follow = next_screen if result.code == 0 and next_screen else screen
    return StepResult(result.code, result.stdout, result.stderr, follow)


def _attempt_of(env: MenuEnvironment, item: Item) -> Attempt:
    assert item.attempt_id is not None
    return find_attempt(load_history(env.practice_dir), item.attempt_id)


def _active(history: History, platform: str | None, problem_id: str | None) -> Screen:
    attempt = latest_unfinished(history, platform, problem_id)
    if attempt is None:
        raise AttemptError("no unfinished attempt was found after the action")
    return Screen("attempt", attempt_id=attempt.attempt_id)


def _resume(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    result = env.run(["attempt", "resume"])
    follow = _active(load_history(env.practice_dir), None, None)
    return StepResult(result.code, result.stdout, result.stderr, follow)


def _resume_problem(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    result = env.run(["attempt", "resume", screen.platform, screen.problem_id])
    follow = _active(load_history(env.practice_dir), screen.platform, screen.problem_id)
    return StepResult(result.code, result.stdout, result.stderr, follow)


def _browse(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    return StepResult(0, "", "", Screen("browse"))


def _progress(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    return _run(env, screen, ["progress"], None)


def _select(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    assert item.problem is not None
    platform, problem_id = item.problem
    return StepResult(
        0, "", "", Screen("problem", platform=platform, problem_id=problem_id)
    )


def _start(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    assert item.problem is not None
    platform, problem_id = item.problem
    argv = ["attempt", "start", platform, problem_id]
    result = env.run([*argv, *_package_flags(env, platform, problem_id)])
    if result.code != 0:
        return StepResult(result.code, result.stdout, result.stderr, screen)
    follow = _active(load_history(env.practice_dir), platform, problem_id)
    return StepResult(0, result.stdout, result.stderr, follow)


def _test(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    attempt = _attempt_of(env, item)
    argv = ["attempt", "test", attempt.attempt_id]
    flags = _package_flags(env, attempt.platform, attempt.problem_id)
    return _run(env, screen, [*argv, *flags], None)


def _request(action: str, *extra: str) -> Callable[..., StepResult]:
    def prepare(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
        attempt = _attempt_of(env, item)
        argv = ["request", attempt.attempt_id, "--action", action, *extra]
        flags = _package_flags(env, attempt.platform, attempt.problem_id)
        return _run(env, screen, [*argv, *flags], None)

    return prepare


def _notes(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    attempt = _attempt_of(env, item)
    notes = env.run(["notes", attempt.attempt_id])
    progress = env.run(["progress", attempt.platform, attempt.problem_id])
    code = notes.code or progress.code
    return StepResult(
        code, notes.stdout + progress.stdout, notes.stderr + progress.stderr, screen
    )


def _reviews(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    return StepResult(0, "", "", Screen("reviews"))


def _review_start(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    assert item.problem is not None
    platform, problem_id = item.problem
    argv = ["review", "start", platform, problem_id, "--language", item.language]
    result = env.run([*argv, *_package_flags(env, platform, problem_id)])
    if result.code != 0:
        return StepResult(result.code, result.stdout, result.stderr, screen)
    follow = _active(load_history(env.practice_dir), platform, problem_id)
    return StepResult(0, result.stdout, result.stderr, follow)


def _review_resume(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    assert item.problem is not None and item.attempt_id is not None
    platform, problem_id = item.problem
    result = env.run(["attempt", "resume", platform, problem_id])
    follow = Screen("attempt", attempt_id=item.attempt_id)
    return StepResult(result.code, result.stdout, result.stderr, follow)


def _recommendations(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    return StepResult(0, "", "", Screen("recommend"))


def _main(env: MenuEnvironment, screen: Screen, item: Item) -> StepResult:
    return StepResult(0, "", "", MAIN)


_ACTIONS: dict[str, Callable[[MenuEnvironment, Screen, Item], StepResult]] = {
    "resume": _resume,
    "resume-problem": _resume_problem,
    "browse": _browse,
    "progress": _progress,
    "select": _select,
    "start": _start,
    "test": _test,
    "hint": _request("hint"),
    "explain-approach": _request("explain-my-approach"),
    "explain-solution": _request("explain-solution", "--reveal", "solution"),
    "notes": _notes,
    "reviews": _reviews,
    "recommendations": _recommendations,
    "review-start": _review_start,
    "review-resume": _review_resume,
    "main": _main,
}
