# -*- coding: utf-8 -*-
# Verify that xutils.tokenizer can tokenize project .py source files without
# raising an exception (a lightweight syntax-parsing check).
import os
import typing

import xutils.tokenizer as tokenizer


# directories that are not project source code
_SKIP_DIRS = {
    ".git",
    "__pycache__",
    "htmlcov",
    "testdata",
    "data",
    "static",
    "node_modules",
    "venv",
    ".venv",
    "xnote_web.egg-info",
}

# the three core libraries to tokenize in the focused test
_LIB_DIRS = ("xnote", "xnote_handlers", "xutils")


def _project_root() -> str:
    # tests/ -> project root is the parent directory
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _iter_py_files(root: str) -> typing.Iterator[str]:
    for dirpath, dirnames, filenames in os.walk(root):
        # prune skipped directories in place so os.walk does not descend
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield os.path.join(dirpath, name)


def _tokenize_files(paths: typing.Iterable[str]) -> typing.List[str]:
    """Tokenize each file; return a list of "<relpath>: <error>" failure strings."""
    root = _project_root()
    failures = []  # type: typing.List[str]
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as fp:
                content = fp.read()
        except Exception:
            # skip files that cannot be decoded as utf-8 text
            continue
        try:
            tokenizer.tokenize(content)
        except Exception as e:
            rel = os.path.relpath(path, root)
            failures.append("%s: %s" % (rel, e))
    return failures


class TestTokenizerParseAllFiles:

    def test_all_py_files_tokenize(self):
        failures = _tokenize_files(_iter_py_files(_project_root()))
        assert not failures, (
            "tokenizer failed on %d file(s):\n" % len(failures)
            + "\n".join(failures[:100])
        )

    def test_tokenize_core_libs(self):
        root = _project_root()
        paths = []  # type: typing.List[str]
        for lib in _LIB_DIRS:
            lib_dir = os.path.join(root, lib)
            assert os.path.isdir(lib_dir), "missing library dir: %s" % lib
            paths.extend(_iter_py_files(lib_dir))
        assert len(paths) > 0, "no .py files found in %s" % (", ".join(_LIB_DIRS))
        failures = _tokenize_files(paths)
        assert not failures, (
            "tokenizer failed on %d file(s) in core libs:\n" % len(failures)
            + "\n".join(failures[:100])
        )
