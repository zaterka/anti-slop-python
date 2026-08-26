"""Tests for inline suppression comments."""

from __future__ import annotations

from anti_slop.suppressions import parse_suppressions

RULE = "anti-slop/no-any-parameters"
OTHER = "anti-slop/no-debug-prints"


def test_trailing_comment_suppresses_its_own_line() -> None:
    source = "def f(x: Any) -> None: ...  # anti-slop: ignore[no-any-parameters]\n"
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(RULE, 1)
    assert not suppressions.suppresses(OTHER, 1)
    assert not suppressions.suppresses(RULE, 2)


def test_own_line_comment_suppresses_the_line_below() -> None:
    source = "# anti-slop: ignore[no-any-parameters]\ndef f(x: Any) -> None: ...\n"
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(RULE, 2)


def test_trailing_comment_does_not_leak_to_the_next_line() -> None:
    """A trailing comment refers to its own statement, never the one after it."""
    source = (
        "print(a)  # anti-slop: ignore[no-debug-prints]\n"
        "print(b)\n"
    )
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(OTHER, 1)
    assert not suppressions.suppresses(OTHER, 2)


def test_bare_ignore_suppresses_every_rule_on_the_line() -> None:
    suppressions = parse_suppressions("f(x)  # anti-slop: ignore\n")

    assert suppressions.suppresses(RULE, 1)
    assert suppressions.suppresses(OTHER, 1)


def test_rule_names_may_be_bare_or_qualified() -> None:
    bare = parse_suppressions("f(x)  # anti-slop: ignore[no-any-parameters]\n")
    qualified = parse_suppressions(
        "f(x)  # anti-slop: ignore[anti-slop/no-any-parameters]\n"
    )

    assert bare.suppresses(RULE, 1)
    assert qualified.suppresses(RULE, 1)


def test_multiple_rules_in_one_directive() -> None:
    source = "f(x)  # anti-slop: ignore[no-any-parameters, no-debug-prints]\n"
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(RULE, 1)
    assert suppressions.suppresses(OTHER, 1)


def test_ignore_file_applies_to_the_whole_file() -> None:
    suppressions = parse_suppressions(
        "# anti-slop: ignore-file[no-any-parameters]\nx = 1\n"
    )

    assert suppressions.suppresses(RULE, 1)
    assert suppressions.suppresses(RULE, 99)
    assert not suppressions.suppresses(OTHER, 99)


def test_trailing_prose_after_the_directive_is_allowed() -> None:
    source = "f(x)  # anti-slop: ignore[no-eval-exec] input is a trusted literal\n"
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses("anti-slop/no-eval-exec", 1)


def test_ordinary_comments_suppress_nothing() -> None:
    suppressions = parse_suppressions("f(x)  # ignore this, it is fine\n")

    assert not suppressions
    assert not suppressions.suppresses(RULE, 1)


def test_unparseable_source_suppresses_nothing() -> None:
    """A file that will not tokenize must not silently suppress everything."""
    suppressions = parse_suppressions("def broken(  # anti-slop: ignore\n")

    assert not suppressions.suppresses(RULE, 1)


def test_directive_heads_a_multiline_comment_block() -> None:
    """The explanation may run past the directive line onto the code below."""
    source = (
        "# anti-slop: ignore[no-any-parameters] this seam is exercised\n"
        "# by the contract tests, which own the parsing.\n"
        "def f(x: Any) -> None: ...\n"
    )
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(RULE, 3)


def test_blank_line_detaches_the_directive() -> None:
    source = "# anti-slop: ignore[no-any-parameters]\n\ndef f(x: Any) -> None: ...\n"
    suppressions = parse_suppressions(source)

    assert not suppressions.suppresses(RULE, 3)


def test_indented_own_line_directive_reaches_its_statement() -> None:
    source = (
        "class C:\n"
        "    # anti-slop: ignore[no-any-parameters]\n"
        "    def m(self, x: Any) -> None: ...\n"
    )
    suppressions = parse_suppressions(source)

    assert suppressions.suppresses(RULE, 3)


def test_trailing_directive_at_end_of_file_does_not_crash() -> None:
    assert parse_suppressions("x = 1\n# anti-slop: ignore[no-any-parameters]\n")
