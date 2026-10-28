# ABOUTME: Child process script that imports a solution and calls it once per case.
# ABOUTME: Standard library only; reports one JSON event per line on a private channel.

import importlib.util
import json
import os
import sys
import traceback
from typing import Any, TextIO

TRACEBACK_LIMIT = 1500


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

    for case in payload["cases"]:
        case_id = case["id"]
        emit(channel, {"event": "start", "case": case_id})
        # Fresh arguments for every case: decoded from text each time.
        args = json.loads(case["args_json"])
        try:
            value = function(*args)
        except BaseException:
            emit(
                channel,
                {"event": "case_error", "case": case_id} | describe_current_exception(),
            )
            continue
        try:
            json.dumps(value, allow_nan=False)
        except (TypeError, ValueError, RecursionError) as error:
            detail = f"{type(value).__name__} is not JSON data: {error}"
            emit(
                channel, {"event": "unserializable", "case": case_id, "detail": detail}
            )
            continue
        emit(channel, {"event": "result", "case": case_id, "value": value})
    emit(channel, {"event": "done"})


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
