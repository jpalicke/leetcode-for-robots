# ABOUTME: Child process script that imports a solution and calls it once per case.
# ABOUTME: Standard library only; reports one JSON event per line on a private channel.

import importlib.util
import json
import operator
import os
import sys
import traceback
from collections.abc import Iterator
from typing import Any, SupportsIndex, TextIO

TRACEBACK_LIMIT = 1500


class ProbeList(list[Any]):
    """A list that records which positions the solution looked at.

    Only distinct positions count, so reading the same entry several times in one
    step costs one. Operations that read the whole list (iteration, membership,
    copying, comparing, sorting) count every position they read. Slices count the
    positions they copy and return a plain list. len() is free. C code that reads
    the list's buffer directly, such as the heapq functions, cannot be seen.
    """

    def __init__(self, items: Any = ()) -> None:
        super().__init__(items)
        self._looked_at: set[int] = set()

    @property
    def probe_count(self) -> int:
        return len(self._looked_at)

    def _look_at_all(self) -> None:
        self._looked_at.update(range(len(self)))

    def _items(self) -> list[Any]:
        """A plain copy of the contents, reading every position."""
        self._look_at_all()
        return list(list.__iter__(self))

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, slice):
            self._looked_at.update(range(*key.indices(len(self))))
            return list(list.__getitem__(self, key))
        value = list.__getitem__(self, key)  # Raises IndexError when out of range.
        index = operator.index(key)
        self._looked_at.add(index + len(self) if index < 0 else index)
        return value

    def __iter__(self) -> Iterator[Any]:
        for index in range(len(self)):
            self._looked_at.add(index)
            yield list.__getitem__(self, index)

    def __reversed__(self) -> Iterator[Any]:
        for index in range(len(self) - 1, -1, -1):
            self._looked_at.add(index)
            yield list.__getitem__(self, index)

    def __contains__(self, value: object) -> bool:
        for index in range(len(self)):
            self._looked_at.add(index)
            item = list.__getitem__(self, index)
            if item is value or item == value:
                return True
        return False

    def index(
        self,
        value: Any,
        start: SupportsIndex = 0,
        stop: SupportsIndex = sys.maxsize,
    ) -> int:
        first, last, _ = slice(start, stop).indices(len(self))
        for index in range(first, last):
            self._looked_at.add(index)
            item = list.__getitem__(self, index)
            if item is value or item == value:
                return index
        raise ValueError(f"{value!r} is not in list")

    def count(self, value: Any) -> int:
        self._look_at_all()
        return list.count(self, value)

    def copy(self) -> list[Any]:
        return self._items()

    def sort(self, *, key: Any = None, reverse: bool = False) -> None:
        self._look_at_all()
        list.sort(self, key=key, reverse=reverse)

    def __add__(self, other: Any) -> list[Any]:
        self._look_at_all()
        return list.__add__(self, other)

    def __radd__(self, other: Any) -> Any:
        if not isinstance(other, list):
            return NotImplemented
        return list.__add__(other, self._items())

    def __mul__(self, count: Any) -> list[Any]:
        self._look_at_all()
        return list.__mul__(self, count)

    __rmul__ = __mul__

    def __eq__(self, other: object) -> bool:
        self._look_at_all()
        return list.__eq__(self, other)

    def __ne__(self, other: object) -> bool:
        self._look_at_all()
        return list.__ne__(self, other)

    def __lt__(self, other: Any) -> bool:
        self._look_at_all()
        return list.__lt__(self, other)

    def __le__(self, other: Any) -> bool:
        self._look_at_all()
        return list.__le__(self, other)

    def __gt__(self, other: Any) -> bool:
        self._look_at_all()
        return list.__gt__(self, other)

    def __ge__(self, other: Any) -> bool:
        self._look_at_all()
        return list.__ge__(self, other)

    __hash__ = None

    def __repr__(self) -> str:
        return repr(self._items())


def describe_current_exception() -> dict[str, str]:
    error = sys.exc_info()[1]
    assert error is not None
    return {
        "type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc()[-TRACEBACK_LIMIT:],
    }


def emit(channel: TextIO, event: dict[str, Any]) -> None:
    channel.write(json.dumps(event) + "\n")
    channel.flush()


def main(payload_path: str, solution_path: str) -> None:
    # Keep results off the learner's stdout: copy the original stdout for our
    # events, then point stdout at stderr so stray prints cannot corrupt them.
    channel = os.fdopen(os.dup(1), "w", encoding="ascii", newline="\n")
    os.dup2(2, 1)

    with open(payload_path, encoding="utf-8") as payload_file:
        payload = json.load(payload_file)

    try:
        spec = importlib.util.spec_from_file_location("solution", solution_path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except BaseException:
        emit(channel, {"event": "import_error", **describe_current_exception()})
        return
    function = getattr(module, payload["function"], None)
    if not callable(function):
        emit(channel, {"event": "missing_callable", "name": payload["function"]})
        return

    probe_index = payload.get("probe_argument")
    for case in payload["cases"]:
        case_id = case["id"]
        emit(channel, {"event": "start", "case": case_id})
        # Fresh arguments for every case: decoded from text each time.
        args = json.loads(case["args_json"])
        watched = None
        if probe_index is not None:
            watched = ProbeList(args[probe_index])
            args[probe_index] = watched
        try:
            value = function(*args)
        except BaseException:
            emit(
                channel,
                {"event": "case_error", "case": case_id} | describe_current_exception(),
            )
            continue
        probes = watched.probe_count if watched is not None else 0
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as error:
            detail = f"{type(value).__name__} is not JSON data: {error}"
            emit(
                channel, {"event": "unserializable", "case": case_id, "detail": detail}
            )
            continue
        result: dict[str, Any] = {"event": "result", "case": case_id, "value": value}
        if watched is not None:
            result["probes"] = probes
        emit(channel, result)
    emit(channel, {"event": "done"})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
