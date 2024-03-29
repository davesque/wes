from typing import Callable

import pytest

from wes.exceptions import EndOfTokens, Message
from wes.lexer import DISJOINED, Eof, Lexer, Newline, Text, TokenStream, tokenize

from .utils import Eq


def test_tokenize() -> None:
    assert list(tokenize("")) == []
    assert list(tokenize("a")) == ["a"]
    assert list(tokenize("\n")) == ["\n"]
    assert list(tokenize("a\n")) == ["a", "\n"]
    assert list(tokenize("\na")) == ["\n", "a"]
    assert list(tokenize("foo:\nbar")) == ["foo", ":", "\n", "bar"]
    assert list(tokenize("foo:bar   \n\rbaz\n\n")) == [
        "foo",
        ":",
        "bar",
        "   \n\r",
        "baz",
        "\n\n",
    ]


def test_lexer_empty() -> None:
    # no newlines unless statements are given
    assert list(Lexer.from_str("")) == [Eof(0, 0, 0)]
    assert list(Lexer.from_str("\n")) == [Eof(0, 1, 1)]
    assert list(Lexer.from_str(" \n \t \n")) == [Eof(2, 2, 4)]


def test_lexer_simple() -> None:
    lexer = Lexer.from_str(
        """
; test comment
    lda 1
42  ; test comment
"""
    )
    assert list(lexer) == [
        Text("lda", 16, 3, 4),
        Text("1", 16, 3, 8),
        Newline(16, 3, 9),
        Text("42", 26, 4, 0),
        Newline(26, 4, 18),
        Eof(26, 4, 19),
    ]


def test_lexer_complex() -> None:
    lexer = Lexer.from_str(
        """
; Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
; before halting

lda init

count_up:
  out
  add incr
  jc count_down  ; jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         ; jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    assert list(lexer) == [
        Text("lda", 92, 5, 0),
        Text("init", 92, 5, 4),
        Newline(92, 5, 8),
        Text("count_up", 102, 7, 0),
        Text(":", 102, 7, 8),
        Newline(102, 7, 9),
        Text("out", 112, 8, 2),
        Newline(112, 8, 5),
        Text("add", 118, 9, 2),
        Text("incr", 118, 9, 6),
        Newline(118, 9, 10),
        Text("jc", 129, 10, 2),
        Text("count_down", 129, 10, 5),
        Newline(129, 10, 56),
        Text("jmp", 186, 11, 2),
        Text("count_up", 186, 11, 6),
        Newline(186, 11, 14),
        Text("count_down", 202, 13, 0),
        Text(":", 202, 13, 10),
        Newline(202, 13, 11),
        Text("out", 214, 14, 2),
        Newline(214, 14, 5),
        Text("sub", 220, 15, 2),
        Text("incr", 220, 15, 6),
        Newline(220, 15, 10),
        Text("jz", 231, 16, 2),
        Text("end", 231, 16, 5),
        Newline(231, 16, 47),
        Text("jmp", 279, 17, 2),
        Text("count_down", 279, 17, 6),
        Newline(279, 17, 16),
        Text("end", 297, 19, 0),
        Text(":", 297, 19, 3),
        Text("hlt", 297, 19, 5),
        Newline(297, 19, 8),
        Text("init", 307, 21, 0),
        Text(":", 307, 21, 4),
        Text("42", 307, 21, 6),
        Newline(307, 21, 8),
        Text("incr", 316, 22, 0),
        Text(":", 316, 22, 4),
        Text("1", 316, 22, 6),
        Newline(316, 22, 7),
        Eof(316, 22, 8),
    ]


def test_lexer_comma() -> None:
    lexer = Lexer.from_str(
        """
lda a,1
lda a , 1
"""
    )
    assert list(lexer) == [
        Text("lda", 1, 2, 0),
        Text("a", 1, 2, 4),
        Text(",", 1, 2, 5),
        Text("1", 1, 2, 6),
        Newline(1, 2, 7),
        Text("lda", 9, 3, 0),
        Text("a", 9, 3, 4),
        Text(",", 9, 3, 6),
        Text("1", 9, 3, 8),
        Newline(9, 3, 9),
        Eof(9, 3, 10),
    ]


def test_token_stream() -> None:
    text = """
lda a, 1
foo 42, 0x2a
"""
    expected = list(Lexer.from_str(text))

    toks = TokenStream(Lexer.from_str(text))
    # we can assert internal state, can't we?
    assert toks.hist == []
    assert toks.i == 0

    actual = [toks.get() for _ in range(len(expected))]
    assert actual == expected

    for i in range(1, len(expected)):
        toks.reset(i)
        assert toks.mark() == i

        actual = [toks.get() for _ in range(i, len(expected))]
        assert actual == expected[i:]

    with pytest.raises(EndOfTokens):
        toks.get()


@pytest.mark.parametrize(
    "file_txt,check_msg",
    (
        ("(", Eq("unmatched opening delimiter '('")),
        ("[", Eq("unmatched opening delimiter '['")),
        (")", Eq("unmatched closing delimiter ')'")),
        ("]", Eq("unmatched closing delimiter ']'")),
        ("(]", Eq("delimiter mistmatch: expected ')', got ']'")),
        ("[)", Eq("delimiter mistmatch: expected ']', got ')'")),
    ),
)
def test_lexer_delimeter_errors(
    file_txt: str, check_msg: Callable[[str], bool]
) -> None:
    lexer = Lexer.from_str(file_txt)

    with pytest.raises(Message) as excinfo:
        list(lexer)

    assert check_msg(excinfo.value.msg)


def test_lexer_delimeters() -> None:
    lexer = Lexer.from_str(
        """
(
[
(([[
a
]]))
]
)
b
"""
    )
    assert list(lexer) == [
        Text("(", 1, 2, 0),
        Text("[", 3, 3, 0),
        Text("(", 5, 4, 0),
        Text("(", 5, 4, 1),
        Text("[", 5, 4, 2),
        Text("[", 5, 4, 3),
        Text("a", 10, 5, 0),
        Text("]", 12, 6, 0),
        Text("]", 12, 6, 1),
        Text(")", 12, 6, 2),
        Text(")", 12, 6, 3),
        Text("]", 17, 7, 0),
        Text(")", 19, 8, 0),
        Newline(19, 8, 1),
        Text("b", 21, 9, 0),
        Newline(21, 9, 1),
        Eof(21, 9, 2),
    ]


def test_lexer_char_types() -> None:
    lexer = Lexer.from_str(f"***<<>>==*<>={DISJOINED}")

    assert list(lexer) == [
        Text("***", 0, 1, 0),
        Text("<<", 0, 1, 3),
        Text(">>", 0, 1, 5),
        Text("==", 0, 1, 7),
        Text("*", 0, 1, 9),
        Text("<", 0, 1, 10),
        Text(">", 0, 1, 11),
        Text("=", 0, 1, 12),
    ] + [Text(c, 0, 1, 13 + i) for i, c in enumerate(DISJOINED)] + [
        Newline(0, 1, 27),
        Eof(0, 1, 27),
    ]
