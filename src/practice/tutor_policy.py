# ABOUTME: Machine checks for the tutor contract: rule IDs, scoping and private state.
# ABOUTME: Every check returns a list of problems; an empty list means the check passed.

import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

from practice.classification import ALL_CLASSES

POLICY_PATH = "tutor/TUTOR.md"
START_PATH = "tutor/START.md"
DEV_RULES_PATH = "CLAUDE.md"
ROOT_AGENTS_PATH = "AGENTS.md"
CURSOR_RULES_DIR = ".cursor/rules"
CURSOR_RULE_SUFFIXES = (".mdc", ".md")

REQUIRED_RULE_IDS = tuple(f"TUTOR-{number:03d}" for number in range(1, 20))

CLASSES_BEGIN = "<!-- practice:content-classes:begin -->"
CLASSES_END = "<!-- practice:content-classes:end -->"

# Paths that learner state can occupy. Each must be ignored by a committed
# .gitignore, and nothing under .practice may be tracked.
PRIVATE_STATE_DIR = ".practice"
PRIVATE_STATE_PATHS = (
    ".practice/journal.jsonl",
    ".practice/attempts/leetcode-1/attempt/solution.py",
)

# Names of the techniques behind the starter problems. Tutor text must never say
# them, because instruction files are read in every practice session.
TECHNIQUE_TERMS = (
    "hash map",
    "hash table",
    "hash set",
    "hashmap",
    "hashset",
    "dictionary",
    "complement",
    "two pointers",
    "two-pointer",
    "sliding window",
    "stack",
    "binary search",
    "sorting",
    "frequency count",
    "kadane",
    "prefix sum",
    "dynamic programming",
    "greedy",
)

_RULE_DEFINITION = re.compile(r"^- \*\*(TUTOR-\d{3})\*\*", re.MULTILINE)
_RULE_MENTION = re.compile(r"TUTOR-\d{3}")
_CLASS_LINE = re.compile(r"^- `([a-z_]+)`: (open|spoiler)\s*$", re.MULTILINE)
_FENCED = re.compile(r"```.*?```", re.DOTALL)
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_IMPORT = re.compile(r"(?<!\S)@(\S+)")
MIN_COPIED_LINE = 40


def parse_rule_ids(text: str) -> list[str]:
    """Rule IDs defined as `- **TUTOR-NNN**` bullets, in file order."""
    return _RULE_DEFINITION.findall(text)


def render_class_lines() -> list[str]:
    """The class list the policy must carry, from the one vocabulary."""
    return [
        f"- `{name}`: {'spoiler' if entry.spoiler else 'open'}"
        for name, entry in ALL_CLASSES.items()
    ]


def parse_class_lines(text: str) -> dict[str, str]:
    return {name: flag for name, flag in _CLASS_LINE.findall(text)}


def _class_block(text: str) -> str | None:
    start = text.find(CLASSES_BEGIN)
    end = text.find(CLASSES_END)
    if start == -1 or end == -1 or end < start:
        return None
    return text[start + len(CLASSES_BEGIN) : end]


def check_policy_text(text: str) -> list[str]:
    problems: list[str] = []
    found = parse_rule_ids(text)
    for rule_id, count in Counter(found).items():
        if count > 1:
            problems.append(f"{POLICY_PATH}: duplicate rule {rule_id} ({count} times)")
    for rule_id in REQUIRED_RULE_IDS:
        if rule_id not in found:
            problems.append(f"{POLICY_PATH}: required rule {rule_id} is missing")
    for rule_id in sorted(set(found) - set(REQUIRED_RULE_IDS)):
        problems.append(f"{POLICY_PATH}: unknown rule {rule_id}")
    problems.extend(_check_class_block(text))
    return problems


def _check_class_block(text: str) -> list[str]:
    block = _class_block(text)
    if block is None:
        return [
            f"{POLICY_PATH}: the content class list between {CLASSES_BEGIN} and "
            f"{CLASSES_END} is missing; `practice tutor classes` prints it"
        ]
    listed = _CLASS_LINE.findall(block)
    problems = [
        f"{POLICY_PATH}: content class {name} is listed more than once"
        for name, count in Counter(name for name, _ in listed).items()
        if count > 1
    ]
    flags = dict(listed)
    for name, entry in ALL_CLASSES.items():
        expected = "spoiler" if entry.spoiler else "open"
        if name not in flags:
            problems.append(f"{POLICY_PATH}: content class {name} is missing")
        elif flags[name] != expected:
            problems.append(
                f"{POLICY_PATH}: content class {name} is {flags[name]} but the "
                f"vocabulary says {expected}"
            )
    for name in flags:
        if name not in ALL_CLASSES:
            problems.append(
                f"{POLICY_PATH}: content class {name} is not in the vocabulary"
            )
    return problems


def find_technique_terms(text: str) -> list[str]:
    found = []
    for term in TECHNIQUE_TERMS:
        pattern = (
            r"\b" + r"[\s-]+".join(re.escape(part) for part in term.split()) + r"\b"
        )
        if re.search(pattern, text, re.IGNORECASE):
            found.append(term)
    return found


def _policy_lines(policy_text: str) -> set[str]:
    lines = {line.strip() for line in policy_text.splitlines()}
    return {line for line in lines if len(line) >= MIN_COPIED_LINE}


def _copied_lines(text: str, policy_text: str) -> list[str]:
    policy = _policy_lines(policy_text)
    return [line.strip() for line in text.splitlines() if line.strip() in policy]


def _strip_code(text: str) -> str:
    return _CODE_SPAN.sub("", _FENCED.sub("", text))


def check_dev_rules(text: str, policy_text: str) -> list[str]:
    problems = []
    for target in _IMPORT.findall(_strip_code(text)):
        if "tutor" in target.lower():
            problems.append(f"{DEV_RULES_PATH}: imports the tutor policy (@{target})")
    if _RULE_MENTION.search(text):
        problems.append(f"{DEV_RULES_PATH}: names a tutor rule ID; keep the policy out")
    if _copied_lines(text, policy_text):
        problems.append(f"{DEV_RULES_PATH}: copies lines from {POLICY_PATH}")
    return problems


def _frontmatter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields


def check_cursor_rule(files: dict[str, str], policy_text: str) -> list[str]:
    """Cursor rules, if any exist, may only point at the tutor policy."""
    problems = []
    for name, text in sorted(files.items()):
        where = f"{CURSOR_RULES_DIR}/{name}"
        fields = _frontmatter(text)
        if fields.get("alwaysApply", "false").lower() == "true":
            problems.append(
                f"{where}: alwaysApply is true; it would apply to development"
            )
        if fields.get("globs"):
            problems.append(f"{where}: globs would attach it to development files")
        if fields.get("description"):
            problems.append(f"{where}: a description lets Cursor apply it on its own")
        if POLICY_PATH not in text:
            problems.append(f"{where}: does not point at {POLICY_PATH}")
        if _RULE_MENTION.search(text):
            problems.append(f"{where}: carries a tutor rule ID; it may only point")
        if _copied_lines(text, policy_text):
            problems.append(f"{where}: copies lines from {POLICY_PATH}")
    return problems


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=60,
    )


def check_private_state(root: Path) -> list[str]:
    """Ask real Git whether learner state is ignored by a .gitignore and untracked."""
    if shutil.which("git") is None:
        return ["git is not on PATH, so private-state ignores cannot be verified"]
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0:
        return [f"{root} is not a Git repository, so ignores cannot be verified"]
    problems = []
    for path in PRIVATE_STATE_PATHS:
        ignored = _git(root, "check-ignore", "-v", "--no-index", "--", path)
        if ignored.returncode != 0:
            problems.append(f"{path} is not ignored by Git; add {PRIVATE_STATE_DIR}/")
            continue
        source = ignored.stdout.split("\t", 1)[0].split(":", 1)[0]
        if Path(source).name != ".gitignore":
            problems.append(
                f"{path} is ignored only by {source}; commit the rule in .gitignore"
            )
    tracked = _git(root, "ls-files", "--", PRIVATE_STATE_DIR)
    for tracked_path in tracked.stdout.splitlines():
        problems.append(f"{tracked_path} is tracked by Git; private state must not be")
    return problems


def _read(root: Path, relative: str) -> str | None:
    try:
        return (root / relative).read_text(encoding="utf-8")
    except OSError:
        return None


def _cursor_files(root: Path) -> dict[str, str]:
    folder = root / CURSOR_RULES_DIR
    if not folder.is_dir():
        return {}
    files = {}
    for path in sorted(folder.rglob("*")):
        if path.is_file() and path.suffix in CURSOR_RULE_SUFFIXES:
            files[path.relative_to(folder).as_posix()] = path.read_text(
                encoding="utf-8"
            )
    return files


def check_contract(root: Path) -> list[str]:
    """Run every contract check against the repository at root."""
    policy = _read(root, POLICY_PATH)
    if policy is None:
        return [f"{POLICY_PATH} is missing or unreadable"]
    problems = check_policy_text(policy)

    start = _read(root, START_PATH)
    if start is None:
        problems.append(f"{START_PATH} is missing or unreadable")
    elif "TUTOR.md" not in start:
        problems.append(f"{START_PATH}: does not point at {POLICY_PATH}")

    dev_rules = _read(root, DEV_RULES_PATH)
    if dev_rules is None:
        problems.append(f"{DEV_RULES_PATH} (the development rules) is missing")
    else:
        problems.extend(check_dev_rules(dev_rules, policy))
    agents = _read(root, ROOT_AGENTS_PATH)
    if agents is not None and (
        _RULE_MENTION.search(agents) or _copied_lines(agents, policy)
    ):
        problems.append(f"{ROOT_AGENTS_PATH}: must not carry the tutor policy")

    cursor = _cursor_files(root)
    problems.extend(check_cursor_rule(cursor, policy))

    scanned = {POLICY_PATH: policy, START_PATH: start or ""}
    scanned.update({f"{CURSOR_RULES_DIR}/{n}": t for n, t in cursor.items()})
    for name, text in scanned.items():
        for term in find_technique_terms(text):
            problems.append(
                f"{name}: names the technique {term!r}; tutor text must not"
            )

    problems.extend(check_private_state(root))
    return problems
