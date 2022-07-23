from io import StringIO

import pytest

from das.compiler import Compiler
from das.compilers.sap1 import Sap1
from das.exceptions import RenderedError


def test_compiler_find_labels() -> None:
    compiler = Compiler.from_str(
        """
zero: 0x42
one: 0x43
two: 0x44
"""
    )
    compiler.find_labels()

    assert len(compiler.labels) == 3

    assert compiler.labels["zero"] == 0
    assert compiler.labels["one"] == 1
    assert compiler.labels["two"] == 2


def test_compiler_resolve_label() -> None:
    compiler = Compiler.from_str(
        """
lda meaning_of_life
forty_two: 0x42
"""
    )
    compiler.find_labels()

    bad_label_tok = compiler.file.stmts[0].toks[1]
    with pytest.raises(RenderedError) as excinfo:
        compiler.resolve_label("meaning_of_life", bad_label_tok)
    assert excinfo.value.msg == "unrecognized label 'meaning_of_life'"
    assert excinfo.value.toks == (bad_label_tok,)

    good_label_tok = compiler.file.stmts[1].toks[1]
    assert compiler.resolve_label("forty_two", good_label_tok) == 1


def test_find_labels_too_large() -> None:
    compiler = Sap1.from_str(
        """
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
0
too_big
"""
    )
    with pytest.raises(RenderedError) as excinfo:
        list(compiler)

    assert "statement makes program too large" in excinfo.value.msg


def test_find_labels_duplicate_label() -> None:
    compiler = Compiler.from_str(
        """
foo: 1
foo: 1
"""
    )
    with pytest.raises(RenderedError) as excinfo:
        compiler.find_labels()

    assert "redefinition of label" in excinfo.value.msg


def test_compiler_from_str() -> None:
    assert list(Sap1.from_str("255")) == [255]


def test_compiler_from_buf() -> None:
    assert list(Sap1.from_buf(StringIO("255"))) == [255]
