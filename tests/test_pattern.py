from collections import deque
from typing import Any

import pytest

from wes.exceptions import PatternError
from wes.pattern import Pattern, Substitutions, Var, apply_sub, occurs_check, unify


class String(Pattern):
    pass


class Integer(Pattern):
    pass


class Natural(Integer):
    pass


string = String()
integer = Integer()
natural = Natural()


class List(Pattern):
    __slots__ = ("U",)


class Map(Pattern):
    __slots__ = ("K", "V")


def test_pattern_params() -> None:
    assert string.params == ()
    assert List(string).params == (string,)
    assert Map(string, integer).params == (string, integer)


class Array(Pattern):
    __slots__ = ("el_type", "length")


def test_pattern_equal() -> None:
    assert integer.equal(integer)
    assert not string.equal(integer)

    assert List(integer).equal(List(integer))
    assert not List(integer).equal(List(string))

    assert Map(string, integer).equal(Map(string, integer))
    assert not Map(string, string).equal(Map(string, integer))

    assert Array(integer, length=10).equal(Array(integer, length=10))
    assert not Array(integer, length=10).equal(Array(integer, length=9))


def test_pattern_unify() -> None:
    """
    This test is light.  Most tests cover the top-level ``unify`` function in
    the ``pattern`` module.
    """
    assert Map(T, T).unify(Map(integer, integer)) == {T: integer}


def test_pattern_match() -> None:
    assert Map(T, T).match(Map(integer, integer))
    assert not Map(T, T).match(Map(integer, string))


def test_pattern_hash() -> None:
    map_t = Map(string, integer)
    d = {string: "string", map_t: "map"}

    assert d[string] == "string"
    assert d[map_t] == "map"


def test_pattern_eq() -> None:
    assert Integer() == Integer()
    assert String() != Integer()


def test_pattern_repr() -> None:
    assert repr(integer) == "Integer"
    assert repr(List(integer)) == "List(Integer)"
    assert repr(Map(string, integer)) == "Map(String, Integer)"


def string_or_integer(t: Pattern) -> bool:
    return t == string or t == integer


def never_match(_: Pattern) -> bool:
    return False


T = Var("T")
U = Var("U")
V = Var("V", string_or_integer)
W = Var("W", never_match)


def test_var_init() -> None:
    assert T.name == "T"
    assert T.predicate is None

    assert V.name == "V"
    assert V.predicate is string_or_integer


def test_var_repr() -> None:
    assert repr(T) == "T"


def test_var_eq() -> None:
    assert T == Var("T")
    assert T == T
    assert T != U

    assert V == Var("V", string_or_integer)
    assert V != Var("V", never_match)


def test_var_hash() -> None:
    dct = {T: "T"}
    assert dct[T] == "T"


@pytest.mark.parametrize(
    "x,y,sub",
    (
        # bind var directly to val
        (T, integer, {T: integer}),
        (integer, T, {T: integer}),
        # bind nested var
        (List(T), List(string), {T: string}),
        # bind matching vals for same var
        (Map(T, T), Map(integer, integer), {T: integer}),
        # bind same val for different vars
        (Map(T, U), Map(integer, integer), {T: integer, U: integer}),
        # bind different vals for different vars
        (Map(T, U), Map(string, integer), {T: string, U: integer}),
        # bind more deeply nested vars
        (List(Map(T, T)), List(Map(string, string)), {T: string}),
        (
            Map(List(T), U),
            Map(List(integer), string),
            {
                T: integer,
                U: string,
            },
        ),
        # bind var to static value
        (T, 3, {T: 3}),
        # val binds to var with special predicate
        (V, integer, {V: integer}),
        (V, string, {V: string}),
        # both sides have vars
        (Map(T, integer), Map(string, U), {T: string, U: integer}),
        # misc other cases
        (Map(T, T), Map(string, U), {T: string, U: string}),
        (Map(T, U), Map(string, List(T)), {T: string, U: List(string)}),
    ),
)
def test_unify(x: Any, y: Any, sub: Substitutions) -> None:
    assert unify(x, y) == sub
    assert unify(y, x) == sub


@pytest.mark.parametrize(
    "x,y,exc_msg",
    (
        # different vals for same var
        (Map(T, T), Map(integer, string), "type mismatch"),
        # different vals at same level
        (List(T), Map(integer, string), "type mismatch"),
        # var compared with static value
        (List(T), 3, "concrete mismatch"),
        # var predicate rejects val
        (V, List(integer), "did not satisfy predicate"),
        (W, integer, "did not satisfy predicate"),
        # recursive self reference
        (T, List(T), "recursive self reference"),
        (Map(T, U), Map(string, Map(T, U)), "recursive self reference"),
    ),
)
def test_unify_raises(x: Any, y: Any, exc_msg: str) -> None:
    with pytest.raises(PatternError, match=exc_msg):
        unify(x, y)
    with pytest.raises(PatternError, match=exc_msg):
        unify(y, x)


@pytest.mark.parametrize(
    "tv,x,term,expected",
    (
        (T, string, T, string),
        (T, string, U, U),
        (T, string, 1, 1),
        (T, string, List(T), List(string)),
        (T, string, List((T, U)), List((string, U))),
        (T, string, List([T, U]), List([string, U])),
        (T, string, List({"foo": T}), List({"foo": string})),
        (T, string, List(Map(T, U)), List(Map(string, U))),
        (
            T,
            string,
            deque([(T, string), (integer, T)]),
            deque([(string, string), (integer, string)]),
        ),
    ),
)
def test_apply_sub(tv: Var, x: Any, term: Any, expected: Any) -> None:
    assert apply_sub(tv, x, term) == expected


@pytest.mark.parametrize(
    "var,term,expected",
    (
        (T, T, True),
        (T, List(T), True),
        (T, Map(integer, List(T)), True),
        (T, integer, False),
        (T, List(integer), False),
        (T, Map(integer, List(string)), False),
        (T, 1, False),
        (
            T,
            deque([(T, string), (integer, T)]),
            True,
        ),
        (
            T,
            deque([(string, string), (integer, string)]),
            False,
        ),
        (
            T,
            {"foo": T},
            True,
        ),
        (
            T,
            {"foo": "bar"},
            False,
        ),
    ),
)
def test_occurs_check(var: Var, term: Any, expected: bool) -> None:
    assert occurs_check(var, term) is expected
