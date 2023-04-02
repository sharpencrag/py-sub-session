import sys
import importlib.abc
import importlib.machinery

import typing as t
from types import ModuleType
import os
import builtins
import pathlib

# type alias
PathLike = t.Union[str, pathlib.Path]

# default names; these are protected from being deleted from `sys.modules`
_protected_names = [
    "sys",
    "builtins",
    "_frozen_importlib",
    "_imp",
    "_thread",
    "_warnings",
    "_weakref",
    "zipimport",
    "_frozen_importlib_external",
    "_io",
    "marshal",
    "nt",
    "winreg",
    "encodings",
    "codecs",
    "_codecs",
    "encodings.aliases",
    "encodings.utf_8",
    "_signal",
    "__main__",
    "encodings.latin_1",
    "io",
    "abc",
    "_abc",
    "site",
    "os",
    "stat",
    "_stat",
    "_collections_abc",
    "ntpath",
    "posixpath",
    "genericpath",
    "os.path",
    "_sitebuiltins",
    "atexit",
]

# prevents sub-sessions from being garbage-collected
_sub_sessions = []


class Session:
    """Attempts to isolate a section of code from the rest of a python runtime.

    The intent is to increase the flexibility and modularity of utilities that
    have to run within a single python instance, like plugins to DCC software.

    A Session is intended to be used as a context manager, but can also be used
    as a decorator.

    Usage:

        import my_module as a
        with Session():
            import my_module as b
        @Session()
        def func():
            import my_module as c
        func()
        assert a is not b
        assert a is not c
        assert b is not c

    """

    session_stack = []

    def __init__(
        self,
        *,
        keep_global: t.Sequence[str] = (),
        env: t.Optional[dict] = None,
        inherit_env: bool = True,
        paths: t.Optional[t.List[PathLike]] = None,
        inherit_paths: bool = True,
    ):
        """
        Args:
            env: environment variables to set for this session.  An attempt
              will be made to isolate these variables by patching `os.environ`
              and `os.getenv`.
            inherit_env: if True, the environment from the enclosing scope will
              be inherited and overridden by any values in `env`.
            paths: a list of paths to prepend to `sys.path` for this session.
        """
        self.keep_global = keep_global
        self.kept_global = dict()

        self.inherit_env = inherit_env
        self.isolated_env: t.Dict[str, str] = env or {}

        self.inherit_paths = inherit_paths
        self.isolated_paths: t.List[PathLike] = paths or []

        # declarations for type checking
        self.original_path: t.List[str]
        self.original_env: t.Mapping[str, str]
        self.original_sys_modules: t.Dict[str, ModuleType]
        self.isolated_modules: t.Dict[str, ModuleType]

        # keep alive
        _sub_sessions.append(self)

    def __enter__(self):
        self.isolated_modules = {}

        # save original state
        self.original_path = sys.path
        self.original_env = os.environ
        self.original_sys_modules = dict(sys.modules)
        self.original_import = builtins.__import__

        # patches
        self._patch_sys_modules()
        os.environ = self.isolated_env
        sys.path = self.isolated_paths
        builtins.__import__ = self._isolated_import

        if self.inherit_env:
            self.isolated_env.update(self.original_env)

        if self.inherit_paths:
            self.isolated_paths.extend(self.original_path)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # restore global patches
        self._restore_sys_modules()
        os.environ = self.original_env
        sys.path = self.original_path
        builtins.__import__ = self.original_import

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper

    def _isolated_import(self, name, globals=None, locals=None, fromlist=(), level=0):
        module = self.original_import(name, globals, locals, fromlist, level)
        if (
            name
            and module
            and name not in _protected_names
            and name not in self.keep_global
        ):
            self.isolated_modules[module.__name__] = module
        return module

    def _patch_sys_modules(self):
        for mod_name in self.original_sys_modules:
            if (
                mod_name not in _protected_names
                and mod_name not in self.keep_global
                and mod_name in sys.modules
            ):
                del sys.modules[mod_name]

    def _restore_sys_modules(self):
        self._patch_sys_modules()
        sys.modules.update(self.original_sys_modules)

    def reload(self, module):
        self._patch_sys_modules()
        sys.modules.update(self.isolated_modules)
        try:
            importlib.reload(module)
        except Exception:
            raise
        finally:
            self._restore_sys_modules()
