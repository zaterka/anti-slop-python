# anti-slop-python

Opinionated AST rules that reject low-evidence and low-signal Python patterns.

A Python port of [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop)
(TypeScript/JavaScript on Oxlint), built on Python's standard `ast` module.
The entire tool runs on the Python standard library — no runtime
dependencies.

Beyond the port, it ships 11 Python-specific rules covering the most common
model giveaways in Python (swallowed exceptions, debug prints, f-string
logging, mutable defaults, `eval`/`exec`, `utcnow`, no-op assertions,
pointless async, blocking sleeps in async code, and friends). See
[References](#references) for the sources behind them.

## Install

The normal way to use anti-slop is as an installed package:

```bash
pip install "git+https://github.com/zaterka/anti-slop-python.git"
```

(from a local checkout, `pip install .` does the same.) The package installs
the `anti-slop` console script and the `anti_slop` module — and, once
published, the same commands work with `pip install anti-slop-python`:

```bash
anti-slop .                          # lint the current directory
anti-slop src/ tests/                # lint specific paths
anti-slop --format json . > findings.json
anti-slop --select no-eval-exec .    # run one rule
anti-slop --ignore-rule no-debug-prints .
```

Exit codes: `0` clean, `1` findings, `2` the run itself failed — bad usage, an
unreadable configuration file, or a source file that could not be parsed. The
last one matters in CI: a file the linter could not read is not a file that
passed.

## Use it on pull requests

The bundled action lints changed code and annotates each finding inline on the
diff:

```yaml
# .github/workflows/anti-slop.yml
name: anti-slop
on: pull_request

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: zaterka/anti-slop-python@v1
        with:
          paths: src tests
```

It reads `[tool.anti-slop]` from your `pyproject.toml` like the CLI does, so
the workflow above is usually the whole configuration.

To adopt it on an existing codebase without blocking merges on day one, start
advisory and tighten later:

```yaml
      - uses: zaterka/anti-slop-python@v1
        with:
          paths: src
          fail-on-findings: "false"   # annotate the diff, do not fail the job
```

A file that could not be read or parsed fails the job even when
`fail-on-findings` is `false`; that is a broken run, not an opinion.

| Input | Default | Description |
| --- | --- | --- |
| `paths` | `.` | Files or directories to lint, space separated. |
| `config` | *(search upward)* | Explicit `pyproject.toml` / `anti-slop.toml`. |
| `select` | — | Run only these rules (space or comma separated). |
| `ignore-rule` | — | Disable these rules for the run. |
| `fail-on-findings` | `true` | Set to `"false"` to annotate without failing. |
| `python-version` | `3.12` | Python used to run the linter. |

Outputs: `findings` (count) and `exit-code` (`0`/`1`/`2`), so a later step can
branch on the result.

Not using GitHub Actions? Any CI runs the CLI directly — the exit codes above
are the contract:

```bash
pip install "git+https://github.com/zaterka/anti-slop-python.git"
anti-slop src tests
```

## Or vendor the rules

The original anti-slop project is designed to be **vendored, not treated as a
fixed dependency**: copy the rules into your repository, read them, and change
them to match your team's standards. anti-slop-python supports that too — use
it when you want the rules under your version control, editable in place.

### With an agent skill

```bash
npx skills add zaterka/anti-slop-python --skill install-anti-slop
```

Then ask your coding agent to install or configure anti-slop in the current
repository. The skill copies the package, merges the configuration into the
existing `pyproject.toml`, enables the default rule set, and validates the
result.

To inspect available skills first:

```bash
npx skills add zaterka/anti-slop-python --list
```

### Manually

Copy `anti_slop/` into the target repository (for example at
`tools/anti_slop/`) and run it with that directory on the Python path:

```bash
PYTHONPATH=tools python -m anti_slop .
```

After the copy, the vendored files are yours to maintain and make your own.

## Configuration

Rules are enabled by default; the two opt-in naming rules
(`no-shape-in-symbol-names`, `no-numbered-symbol-names`) are off until
explicitly enabled. Configure per project in `pyproject.toml`:

```toml
[tool.anti-slop]
ignore = ["generated/**", "migrations/**"]

# Disable a rule:
[tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
enabled = false

# Enable an opt-in rule:
[tool.anti-slop.rules."anti-slop/no-numbered-symbol-names"]
enabled = true

# Keep a rule, but not everywhere:
[tool.anti-slop.rules."anti-slop/no-debug-prints"]
exclude = ["src/cli.py", "scripts/**"]

# Pass per-rule options (example: allow isinstance inside TypeGuard functions):
[tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
allow_in_type_guards = true
```

A standalone `anti-slop.toml` / `.anti-slop.toml` file is also supported.
`--config FILE` points at an explicit file; otherwise the nearest
`pyproject.toml` with `[tool.anti-slop]` is used.

`ignore` and per-rule `exclude` patterns are matched (via `fnmatch`) against
each file's path relative to **the configuration file's own directory**, so a
pattern means the same thing whether you run `anti-slop .` or `anti-slop src/`.
Caches and VCS directories (`__pycache__`, `.venv`, `.git`, ...) are always
skipped. A file named explicitly on the command line is always linted.

Prefer `exclude` over `enabled = false`: a rule scoped off the two files that
fight it keeps working everywhere else.

### Suppressing a single finding

An opinionated rule needs an escape hatch cheaper than switching it off. A
comment marks one line, or one file, as a deliberate exception:

```python
value = eval(expr)  # anti-slop: ignore[no-eval-exec] expr is a vetted literal

# anti-slop: ignore[no-any-parameters] the decoder at the seam above already
# validated this payload.
def handle(payload: Any) -> None: ...

# anti-slop: ignore-file[no-debug-prints]
```

Rule names may be bare (`no-eval-exec`) or qualified
(`anti-slop/no-eval-exec`), and several may be listed at once. Omitting the
brackets — `# anti-slop: ignore` — suppresses every rule on that line, which is
blunt; naming the rule documents the decision. A comment on its own line
applies to the statement below it, so the reason can run to several lines.
`ignore-file` applies to the whole file wherever it appears.

## Rules

26 rules in total; 24 are enabled by default, 2 are opt-in (marked **opt-in**
below). List them all with `anti-slop --list-rules`.

### Ported from the JS/TS original

- `no-any-parameters` — rejects explicit `Any` function inputs. `*args: Any` / `**kwargs: Any` are exempt (nothing narrower is expressible for a pass-through signature); set `allow_varargs = false` to police them too. The implementation of an `@overload` set is exempt.
- `no-any-returns` — rejects function contracts that return `Any`, `list[Any]`, `Awaitable[Any]`, or a union containing `Any`.
- `no-any-aliases` — rejects aliases that merely conceal `Any`.
- `no-object-parameters` — rejects the broad `object` type on function inputs (comparison/containment dunders exempt: `__eq__(self, other: object)` is the documented convention).
- `no-unsafe-dict-type` — rejects dict-family value contracts (`dict`, `defaultdict`, `OrderedDict`, `DefaultDict`) based on `Any`, `object`, and semantic equivalents.
- `no-chained-casts` — rejects nested `typing.cast` calls that fabricate evidence.
- `no-conditional-empty-dict-spread` — rejects conditional spreads that use `{}` to omit keys.
- `no-module-mocking` — rejects `mock.patch` / `monkeypatch` attribute and dict-item mocking in favor of real dependency seams.
- `no-runtime-isinstance` — requires boundary parsing instead of ad hoc `isinstance` narrowing (narrowing the caught exception is exempt).
- `no-dynamic-getattr` — rejects dynamic attribute access (`getattr`/`hasattr`/`setattr`/`delattr`) with a non-literal name in favor of typed access.
- `no-dynamic-dispatch` — rejects `getattr(obj, name)(...)` dynamic dispatch in favor of typed calls.
- `no-shape-in-symbol-names` — **opt-in** — rejects `shape` in declared symbol names (TS naming vocabulary; collides with numpy/pandas `.shape`).
- `no-known-value-widening` — rejects explicit broad target annotations that discard known value evidence.
- `no-widen-then-assert` — rejects local flows that widen known values and later cast them back.
- `require-safety-comment-for-cast` — requires each `typing.cast` to document its checked invariant.

### Python-specific

These rules have no JS/TS counterpart; they target the giveaways that models
leave behind in Python specifically (see [References](#references)):

- `no-swallowed-exceptions` — rejects broad `except` handlers whose body does nothing with the failure (`pass`, `continue`, `...`, or a lone string); it must be handled, logged, or re-raised.
- `no-debug-prints` — rejects `print` outside the `if __name__ == "__main__":` guard; output belongs in a logger or the program's output channel.
- `no-fstring-logging` — rejects f-strings as logging message arguments; pass the format string and values separately so formatting stays lazy. The receiver must look like a logger, so `parser.error(f"...")` is not flagged; extend the list with `receivers = [...]`.
- `no-mutable-defaults` — rejects mutable literal parameter defaults (`def f(items=[])`); they are shared across calls.
- `no-eval-exec` — rejects `eval`/`exec`; parse dynamic input into typed values instead of executing it.
- `no-utcnow` — rejects `datetime.utcnow()` (deprecated in 3.12, naive); use `datetime.now(timezone.utc)`.
- `no-trivial-asserts` — rejects assertions that can never fail (`assert True`, `assert x is x`, `self.assertEqual(a, a)`, and the always-truthy `assert (cond, "msg")` typo); they look like coverage but check nothing.
- `no-async-without-await` — rejects `async def` functions that do no async work; make them synchronous. Async generators, `async with`, `async for`, and async comprehensions all count as async work and are exempt.
- `no-blocking-sleep-in-async` — rejects `time.sleep` inside async functions; it blocks the event loop.
- `no-dataclass-mutable-defaults` — rejects mutable defaults on dataclass fields (a runtime `ValueError`); use `field(default_factory=...)`. `ClassVar` pseudo-fields are exempt — dataclasses skips them, so a mutable default there is legal and deliberate.
- `no-numbered-symbol-names` — **opt-in** — rejects throwaway identifiers (`data2`, `result_final`); name symbols for their domain role.

The original plugin's optional Effect rule group has no Python counterpart
yet; framework-specific policy belongs in a separate opt-in group you can add
to a vendored copy.

## Design notes

The 15 ported rules map one-for-one onto the JS/TS original
(`Any`/`object` stand in for TS `unknown`/`object`, `typing.cast` for `as`
assertions, the `getattr` family for `Reflect.get`/`Reflect.apply`). A few
port decisions that may surprise a Python reader:

- **`object` is treated as an escape hatch.** In TypeScript the policed
  `object` is a *narrow* type; in Python it is the top type. This port
  assigns it the same "unparsed value" role as `Any` — that's why
  `no-object-parameters` exists at all in a language where `object` is a
  legitimate top type.
- **The JS `cause` parameter exemption was dropped.** It honored the
  `new Error(msg, { cause })` convention; Python exception chaining is
  `raise X from e`, so an `Any`-typed `cause` is flagged like any other
  `Any` input.
- **String annotations resolve.** Quoted forward references are treated like
  any annotation: `dict[str, "Any"]` and `-> "Any"` are caught, while
  `dict[str, "User"]` remains a safe named type.

## Violation examples

Each snippet below is rejected by the named rule.

### `no-any-parameters`

```python
def handle(input: Any) -> None: ...
```

### `no-any-returns`

```python
def load_user() -> Any:
    return raw_payload

def recent() -> list[Any]:
    return rows
```

### `no-any-aliases`

```python
type ExternalValue = Any
```

### `no-object-parameters`

```python
def save(value: object) -> None: ...
```

### `no-unsafe-dict-type`

```python
type Metadata = dict[str, Any]
type Config = defaultdict[str, Any]
```

### `no-chained-casts`

```python
user = cast(User, cast(object, input))
```

### `no-conditional-empty-dict-spread`

```python
options = {
    **(timeout if timeout is not None else {}),
}
options = {**(timeout and {"timeout": timeout} or {})}
```

### `no-module-mocking`

```python
mock.patch("myapp.user_store")
monkeypatch.setitem(d, "key", value)
```

### `no-runtime-isinstance`

```python
if isinstance(input, str):
    use_name(input)
```

Exempt — narrowing the caught exception:

```python
try:
    fetch()
except Exception as exc:
    if isinstance(exc, TimeoutError):
        retry()
```

Projects that write type-guard helpers can permit `isinstance` directly inside
functions annotated with `TypeGuard[...]` / `TypeIs[...]` while continuing to
reject ad hoc checks elsewhere:

```toml
[tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
allow_in_type_guards = true
```

The option defaults to `false`.

### `no-dynamic-getattr`

```python
value = getattr(owner, key)
value = hasattr(owner, key)
setattr(owner, key, fresh)
```

### `no-dynamic-dispatch`

```python
value = getattr(operation, name)(arg)
```

### `no-shape-in-symbol-names` (opt-in)

```python
class UserShape: ...
```

### `no-known-value-widening`

```python
handlers: dict[str, Handler] = {
    "start": start_handler,
}
```

Python has no `satisfies`, so the rule targets explicit `Any`/`object`
annotations placed over syntactically concrete values:

```python
handlers: Any = {"start": start_handler}
```

### `no-widen-then-assert`

```python
loaded = load_user()
stored: Any = loaded
user = cast(User, stored)
```

### `require-safety-comment-for-cast`

```python
user_id = cast(UserId, value)
```

Add a specific justification immediately before a necessary cast:

```python
# SAFETY: parse_user_id validated the identifier before branding it.
user_id = cast(UserId, value)
```

### `no-swallowed-exceptions`

```python
try:
    process(row)
except Exception:
    pass

try:
    process(row)
except Exception:
    ...  # the stub spelling of pass; swallows identically

try:
    process(row)
except Exception:
    "best effort"  # reads as a comment, runs as a no-op
```

### `no-debug-prints`

```python
def submit(order: Order) -> None:
    print(f"submitting {order}")  # debug residue in application code
```

### `no-fstring-logging`

```python
logger.info(f"job {job_id} failed")
# → logger.info("job %s failed", job_id)
```

Exempt — the receiver is not a logger, and eager formatting is correct:

```python
parser.error(f"bad value: {value}")
```

### `no-mutable-defaults`

```python
def add_item(items=[], item=None): ...
# → def add_item(items=None, item=None): items = items or []
```

### `no-eval-exec`

```python
value = eval(expression_from_user)
```

### `no-utcnow`

```python
now = datetime.utcnow()
# → now = datetime.now(timezone.utc)
```

### `no-trivial-asserts`

```python
def test_roundtrip(self):
    self.assertEqual(result, result)  # checks nothing


def test_range(self):
    assert (0 <= score <= 100, "score out of range")  # always-truthy tuple
    # → assert 0 <= score <= 100, "score out of range"
```

### `no-async-without-await`

```python
async def load_cache() -> Mapping:
    return self._cache  # never awaits; make it a plain function
```

Exempt — `async with` and `async for` are async work even with no `await`:

```python
async def fetch(session: ClientSession) -> Response:
    async with session.get(url) as response:
        return response
```

### `no-blocking-sleep-in-async`

```python
async def retry():
    time.sleep(1)  # blocks the event loop
    # → await asyncio.sleep(1)
```

### `no-dataclass-mutable-defaults`

```python
@dataclass
class Batch:
    items: list = []  # ValueError at class creation; shared across instances
    # → items: list = field(default_factory=list)
```

Exempt — `ClassVar` is a pseudo-field that dataclasses skips entirely:

```python
@dataclass
class Batch:
    registry: ClassVar[dict[str, Handler]] = {}
```

### `no-numbered-symbol-names` (opt-in)

```python
data2 = fetch(second_url)
result_final = compute(total)
```

## Self-lint

This repository lints itself with its own ruleset:

```bash
.venv/bin/python -m anti_slop anti_slop tests skills
```

CI runs exactly that, through the action in this repository, so the tool has to
pass its own checks on every pull request.

No rule is switched off wholesale. Two are *scoped* in `pyproject.toml`, each
with a documented justification:

- `no-runtime-isinstance` — `exclude = ["anti_slop/**"]`. This codebase's core
  mechanism *is* `isinstance` dispatch over concrete `ast.*` node classes. Still
  enforced on the tests.
- `no-debug-prints` — excluded for `cli.py` and the installer script only. This
  project *is* a console tool; stdout is its output channel, in those two files
  and nowhere else.

One finding is suppressed inline, in `tests/harness.py`, with its reason in the
comment. The opt-in rules need no entry — they are off by default everywhere.

## Development

```bash
uv venv .venv
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest
```

`anti_slop/` is canonical. Tests mirror the rules: `tests/test_<rule>.py`
exercises `anti_slop/rules/<rule>.py` through the `RuleTester` harness in
`tests/harness.py`. Add focused RuleTester coverage for semantic rule changes.
Pass `options={...}` to `RuleTester` to exercise a rule's configuration.

The parts of a run that belong to no single rule have their own tests:
`test_engine.py` (file discovery, ignore matching, per-rule scoping, contained
rule crashes), `test_cli.py` (exit codes and output formats), and
`test_suppressions.py`.

## References

Sources used when porting the rules and when choosing the Python-specific
ruleset:

The original project:

- [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) — the
  TypeScript/JavaScript rule set this package ports, one rule for one.

Python documentation (the conventions the rules enforce or carve out):

- [PEP 8 — Style Guide for Python Code](https://peps.python.org/pep-0008/) —
  identifier conventions (including the all-uppercase constant exemption used
  by `no-numbered-symbol-names`).
- [typing — Type Hints and Static Type Checkers](https://docs.python.org/3/library/typing.html) —
  the objects protocol with `__eq__(self, other: object)`, which
  `no-object-parameters` exempts.
- [dataclasses — Simple Declarative Mutable Data Containers](https://docs.python.org/3/library/dataclasses.html) —
  why mutable field defaults are a `ValueError`, the basis of
  `no-dataclass-mutable-defaults`.
- [Using the logging module — lazy `%` formatting](https://docs.python.org/3/howto/logging.html) —
  the documented pattern behind `no-fstring-logging`.
- [datetime — Basic date and time types](https://docs.python.org/3/library/datetime.html) —
  the 3.12 deprecation of `datetime.utcnow()`, the basis of `no-utcnow`.

Practitioner surveys of AI-model giveaways in Python (the concrete patterns
behind the Python-specific rules):

- [Was this Python written by a human or an AI? 7 signs to spot LLM-generated code](https://dev.to/dev_tips/was-this-python-written-by-a-human-or-an-ai-7-signs-to-spot-llm-generated-code-3370) —
  over-documented trivial functions, dictionary-style variable names,
  tutorial-mashup structure, and the absence of real-world edge handling.
- [How to Tell If Code Was Written by AI: 9 Tells (2026)](https://justinmckelvey.com/blog/how-to-tell-if-code-was-written-by-ai) —
  rescue-oriented tell list with a Python-specific section: uniformly
  formatted docstrings, swallowed exceptions, leftover `print` debugging,
  generic numbered naming (`data2`, `result_final`), and tests that assert
  nothing.

Research on code smells in LLM-generated code (evidence that smell density
tracks model origin, and that AST-based smell detection is the workable
methodology for this kind of tool):

- [Investigating The Smells of LLM Generated Code](https://arxiv.org/abs/2510.03029) —
  Ghosh, Zhu & Bayley (2025); LLM-generated code shows a materially higher
  incidence of implementation and design smells than human reference
  solutions, measured with static analysis.

## License

MIT
