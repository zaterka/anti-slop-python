# anti-slop-python

Opinionated AST rules that reject low-evidence and low-signal Python patterns.

This is the Python counterpart to
[dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop)
(TypeScript/JavaScript on Oxlint). Like the original, it is meant to be
**vendored, not treated as a fixed dependency**: copy the `anti_slop/` package
into your repository, read the rules, and change them to match your team's
standards. The bundled agent skill handles the initial copy and configuration;
after that, the vendored files are yours to maintain and make your own.

The entire tool runs on the Python standard library — no runtime dependencies.

## Install with an agent skill

```bash
npx skills add pedro.zaterka/anti-slop-python --skill install-anti-slop
```

Then ask your coding agent to install or configure anti-slop in the current
repository. The skill copies the package, merges the configuration into the
existing `pyproject.toml`, enables every rule, and validates the result.

To inspect available skills first:

```bash
npx skills add pedro.zaterka/anti-slop-python --list
```

## Manual local installation

Copy `anti_slop/` into the target repository, for example at
`tools/anti_slop/` (adjust the import path if you rename it), and make it
importable — either add `tools/` to the Python path in your lint command or
install it as a local editable package:

```bash
pip install -e ./tools/anti-slop-package   # if you keep the full package there
```

Then run it:

```bash
anti-slop .              # lint the current directory
anti-slop src/ tests/    # lint specific paths
python -m anti_slop .    # if the console script is not installed
```

Or wire it into your existing checks as a plain command:

```bash
anti-slop --json . > findings.json
```

### Configuration

All rules are enabled by default. Configure per project in `pyproject.toml`:

```toml
[tool.anti-slop]
ignore = ["generated/**", "migrations/**"]

# Disable a rule:
[tool.anti-slop.rules."anti-slop/no-shape-in-symbol-names"]
enabled = false

# Pass per-rule options (example: allow isinstance inside TypeGuard functions):
[tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
allow_in_type_guards = true
```

A standalone `anti-slop.toml` / `.anti-slop.toml` file is also supported.
`--config FILE` points at an explicit file; otherwise the nearest
`pyproject.toml` with `[tool.anti-slop]` is used.

`ignore` patterns are matched (via `fnmatch`) against each file's path
relative to the walked directory. Caches and VCS directories
(`__pycache__`, `.venv`, `.git`, ...) are always skipped.

## Rules

### Generic rules

- `no-any-parameters` — rejects explicit `Any` function inputs except the explicit `cause` convention.
- `no-any-returns` — rejects function contracts that return `Any`, `Awaitable[Any]`, or a union containing `Any`.
- `no-any-aliases` — rejects aliases that merely conceal `Any`.
- `no-object-parameters` — rejects the broad `object` type on function inputs.
- `no-unsafe-dict-type` — rejects dictionary value contracts based on `Any`, `object`, and semantic equivalents.
- `no-chained-casts` — rejects nested `typing.cast` calls that fabricate evidence.
- `no-conditional-empty-dict-spread` — rejects conditional spreads that use `{}` to omit keys.
- `no-module-mocking` — rejects `mock.patch` / `monkeypatch` attribute mocking in favor of real dependency seams.
- `no-runtime-isinstance` — requires boundary parsing instead of ad hoc `isinstance` narrowing.
- `no-dynamic-getattr` — rejects `getattr` with a non-literal name in favor of typed attribute access.
- `no-dynamic-dispatch` — rejects `getattr(obj, name)(...)` dynamic dispatch in favor of typed calls.
- `no-shape-in-symbol-names` — rejects `shape` in declared symbol names.
- `no-known-value-widening` — rejects explicit broad target annotations that discard known value evidence.
- `no-widen-then-assert` — rejects local flows that widen known values and later cast them back.
- `require-safety-comment-for-cast` — requires each `typing.cast` to document its checked invariant.

### How the JS rules map to Python

| anti-slop (JS/TS) | anti-slop-python |
| --- | --- |
| `no-unknown-parameters` | `no-any-parameters` |
| `no-unknown-returns` | `no-any-returns` |
| `no-unknown-type-aliases` | `no-any-aliases` |
| `no-object-parameters` | `no-object-parameters` |
| `no-unsafe-dictionary-type` | `no-unsafe-dict-type` |
| `no-chained-type-assertions` | `no-chained-casts` |
| `no-conditional-empty-object-spread` | `no-conditional-empty-dict-spread` |
| `no-module-mocking` | `no-module-mocking` |
| `no-runtime-typeof` | `no-runtime-isinstance` |
| `no-reflect-get` | `no-dynamic-getattr` |
| `no-reflect-apply` | `no-dynamic-dispatch` |
| `no-shape-in-symbol-names` | `no-shape-in-symbol-names` |
| `no-known-value-widening` | `no-known-value-widening` |
| `no-widen-then-assert` | `no-widen-then-assert` |
| `require-safety-comment-for-type-assertion` | `require-safety-comment-for-cast` |

The JS plugin's optional Effect rule group has no Python counterpart yet;
framework-specific policy belongs in a separate opt-in group you can add to
your vendored copy.

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
```

### `no-module-mocking`

```python
mock.patch("myapp.user_store")
```

### `no-runtime-isinstance`

```python
if isinstance(input, str):
    use_name(input)
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
```

### `no-dynamic-dispatch`

```python
value = getattr(operation, name)(arg)
```

### `no-shape-in-symbol-names`

```python
class UserShape: ...
```

### `no-unknown-parameters` / `no-known-value-widening`

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

## Development

```bash
uv venv .venv
uv pip install --python .venv/bin/python pytest
.venv/bin/python -m pytest
```

`anti_slop/` is canonical. Tests mirror the rules: `tests/test_<rule>.py`
exercises `anti_slop/rules/<rule>.py` through the `RuleTester` harness in
`tests/harness.py`. Add focused RuleTester coverage for semantic rule changes.

## License

MIT
