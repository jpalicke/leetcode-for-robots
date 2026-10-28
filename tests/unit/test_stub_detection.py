# ABOUTME: Unit tests for static stub detection on real source text.
# ABOUTME: A stub is an unwritten function body, never a candidate pass.

from practice.stubs import is_stub


def stub(source: str, *, allow_none: bool = False) -> bool:
    return is_stub(source, "solve", allow_none=allow_none)


def test_pass_only_body_is_a_stub() -> None:
    assert stub("def solve(x):\n    pass\n")


def test_ellipsis_and_docstring_only_bodies_are_stubs() -> None:
    assert stub("def solve(x):\n    ...\n")
    assert stub('def solve(x):\n    """Docs only."""\n')
    assert stub('def solve(x):\n    """Docs."""\n    pass\n')


def test_raising_not_implemented_is_a_stub_in_either_form() -> None:
    assert stub("def solve(x):\n    raise NotImplementedError\n")
    assert stub("def solve(x):\n    raise NotImplementedError('todo')\n")


def test_returning_none_is_a_stub_only_when_the_contract_forbids_none() -> None:
    assert stub("def solve(x):\n    return None\n")
    assert stub("def solve(x):\n    return\n")
    assert not stub("def solve(x):\n    return None\n", allow_none=True)


def test_real_work_is_not_a_stub() -> None:
    assert not stub("def solve(x):\n    return x + 1\n")
    assert not stub("def solve(x):\n    while True:\n        pass\n")
    assert not stub("def solve(x):\n    raise ValueError('bad')\n")


def test_other_functions_and_missing_functions_are_not_stubs() -> None:
    assert not stub("def other(x):\n    pass\n")
    assert not stub("def solve(x):\n    return x\n\ndef other(x):\n    pass\n")


def test_unparseable_source_is_not_judged_a_stub() -> None:
    assert not stub("def solve(x:\n    pass\n")
