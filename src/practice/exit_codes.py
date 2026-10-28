# ABOUTME: Process exit codes shared by every practice command.
# ABOUTME: 0 success, 1 no match or not passed, 2 usage, 3 invalid input.

EXIT_NOT_PASSED = (
    1  # No search match, no attempt to resume, or a run that did not pass.
)
EXIT_USAGE = 2
EXIT_BAD_INPUT = 3  # A corrupt catalog, journal or an invalid exercise package.
