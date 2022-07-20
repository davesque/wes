from das.lexer import tokenize, Token


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


def test_token_is_newline() -> None:
    tok = Token("\n", 0, 0, "", 0, 0, 0)
    assert tok.is_newline

    tok = Token("  \n", 0, 0, "", 0, 0, 0)
    assert not tok.is_newline


def test_token_is_eof() -> None:
    tok = Token("", 0, 0, "", 0, 0, 0)
    assert tok.is_eof

    tok = Token("  \n", 0, 0, "", 0, 0, 0)
    assert not tok.is_eof
