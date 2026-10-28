# ABOUTME: Detects unwritten solution functions by reading source, without running it.
# ABOUTME: A stub body is only pass, an ellipsis, NotImplementedError or return None.

import ast


def is_stub(source: str, function_name: str, *, allow_none: bool) -> bool:
    """True when the named top-level function has no real body yet."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False  # The run reports the syntax error; it is not a stub.
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            if node.name == function_name:
                return all(_is_placeholder(s, allow_none) for s in _body(node))
    return False


def _body(function: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.stmt]:
    body = function.body
    if body and _is_constant_expression(body[0], str):
        return body[1:]  # A docstring alone does not make a function real.
    return body


def _is_constant_expression(statement: ast.stmt, kind: type) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, kind)
    )


def _is_placeholder(statement: ast.stmt, allow_none: bool) -> bool:
    if isinstance(statement, ast.Pass):
        return True
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
        return statement.value.value is Ellipsis
    if isinstance(statement, ast.Raise):
        raised = statement.exc
        if isinstance(raised, ast.Call):
            raised = raised.func
        return isinstance(raised, ast.Name) and raised.id == "NotImplementedError"
    if isinstance(statement, ast.Return) and not allow_none:
        return statement.value is None or (
            isinstance(statement.value, ast.Constant) and statement.value.value is None
        )
    return False
