# py-sub-session
Create "sub-sessions" within a long-running Python instance with isolated imports, environment, and paths.

This solution was originally designed for use in digital content creation systems like
Autodesk Maya, but the import and environment isolation could be
useful for any system with long-running, dynamic python sessions where creating a
sub-process is not feasible.


## Who is this package for?
If you possibly can, use `subprocess` for more-complete isolation within a python application.

This tool is intended for situations where `subprocess` is not available -- one use-case being tools and plugins within Maya or other DCCs that provide a single python interpreter session. Even then, careful design should be a first line of defense.

Unfortunately, you can't always control third-party dependencies, and sometimes you need to import two different versions of a library within the same maya session...

## Extant Solutions
Some similar solutions involve using a function call to isolate imports:

```python
module = unique_import("module")
```

For an example, check out Autodesk Shotgrid Toolkit, where this pattern is often used to manage the code for their apps and framework system.

Using a function wrapper is a straightforward approach and can be extremely robust.

Unfortunately, using a function call in this way has the downside of being opaque to static analysis and code completion.  There are some ways around this, but it often requires setting up a development environment in unintuitive ways, such that something like this works:

```python
try:
    import my_module
except ImportError:
    my_module = unique_import("my_module")
```

`py-sub-session` opts for an approach that emphasizes readability; sub-sessions are defined in context managers, and imports are handled as regular imports.

## Isolating Imports

```python
with subsession.Session():
    import my_module as a

with subsession.Session():
    import my_module as b

assert a is not b
```

Any imports made while the `Session` context manager is active will be
- re-imported, even if previously cached by the import system
- unique to that session

This process attempts to skip modules that are imported as part of python initialization;  Some platform- or interpreter-specific modules might cause unexpected behavior, so an additional mechanism is provided to keep specific modules from being isolated, if your use-case requires:

```python
with subsession.Session(keep_global=["platform_module"]):
    import my_module
    import platform_module
```

In this example, if `platform_module` has already been imported and cached, the cached version will be used.  Put another way, `platform_module` is treated like a regular import without any special isolation sauce.


## Isolating Environment

The `Session` object can also store a local set of environment variables and import paths.

***NOTE:*** The environment variables (via os.environ) and import paths (via sys.path) are ONLY patched while the context manager is active!

```python
local_path = "/path/to/resource"

with subsession.Session(env={"TEST": "test"}, paths=[local_path]):
    import module_at_local_path  # <- discoverable at /path/to/resource
    assert os.getenv("TEST") == "test"
```

## Reloading Modules

Because modules imported within a `Session` aren't kept in sys.modules, `importlib.reload` won't work on any modules created within the session.

To account for this, the `Session` object provides a reload method:
```python
with Session() as s:
    import my_module

s.reload(my_module)
```
