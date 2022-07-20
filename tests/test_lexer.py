from das.lexer import tokenize


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
