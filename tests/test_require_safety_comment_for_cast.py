"""Tests for ``anti-slop/require-safety-comment-for-cast``."""

from anti_slop.rules.require_safety_comment_for_cast import (
    RequireSafetyCommentForCastRule,
)

from tests.harness import RuleTester


def test_require_safety_comment_for_cast() -> None:
    RuleTester(RequireSafetyCommentForCastRule()).run(
        "anti-slop/require-safety-comment-for-cast",
        valid=[
            "from typing import cast\n"
            "# SAFETY: parse_user validated the payload upstream.\n"
            "x = cast(User, raw)",
            # A trailing comment on the cast's own line counts.
            "from typing import cast\n"
            "x = cast(User, raw)  # SAFETY: validated in request middleware",
            "from typing import cast\n"
            "def f(raw) -> User:\n"
            "    # SAFETY: checked invariant\n"
            "    return cast(User, raw)",
            # A comment block after the previous statement satisfies the cast.
            "from typing import cast\n"
            "x = 1\n"
            "# SAFETY: validated upstream\n"
            "y = cast(User, raw)",
            # Two casts on one line share the trailing comment.
            "from typing import cast\n"
            "x = cast(User, raw)  # SAFETY: one comment, one line\n"
            "z = cast(str, x)  # SAFETY: second cast",
            # A local cast function is not typing.cast.
            "def cast(t, v):\n"
            "    return v\n"
            "cast(User, raw)",
        ],
        invalid=[
            {
                "code": "from typing import cast\n"
                "x = cast(User, raw)",
                "count": 1,
            },
            {
                "code": "from typing import cast\n"
                "# This is a comment\n"
                "x = cast(User, raw)",
                "count": 1,
            },
            {
                "code": "from typing import cast\n"
                "x = cast(User, raw)  # just a comment",
                "count": 1,
            },
            {
                "code": (
                    "from typing import cast\n"
                    "def f(raw) -> None:\n"
                    "    g(cast(User, raw))"
                ),
                "count": 1,
            },
            # A comment satisfies only the statement it precedes.
            {
                "code": (
                    "from typing import cast\n"
                    "x = 1\n"
                    "# SAFETY: for the first cast\n"
                    "a = cast(User, raw)\n"
                    "b = cast(User, raw2)"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import cast\n"
                    "x = cast(User, raw)\n"
                    "y = cast(User, raw2)"
                ),
                "count": 2,
            },
        ],
    )
