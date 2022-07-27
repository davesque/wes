from wes.lexer import Eof, Lexer, Newline, Text, tokenize


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
