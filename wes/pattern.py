from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Optional, Tuple

from wes.exceptions import PatternError
from wes.utils import SlotClass


class Pattern(SlotClass):
    __slots__: Tuple[str, ...] = tuple()

    annotations: Tuple[str, ...] = tuple()

    @property
    def params(self) -> Tuple[Any, ...]:
        """
        Return a tuple of parameters provided to a pattern.
        """
        return tuple(
            getattr(self, n) for n in self.__slots__ if n not in self.annotations
        )

    def equal(self, p: Pattern) -> bool:
        """
        Return ``True`` if ``p`` should be considered an instance of *and* an
        equal parameterization of this pattern type.
        """
        return (type(self) is type(p)) and all(
            x == y for x, y in zip(self.params, p.params)
        )

    def unify(self, p: Pattern) -> Substitutions:
        """
        Find a mapping of substitutions that unifies this pattern with the
        pattern ``p``.
        """
        return unify(self, p)

    def match(self, p: Pattern) -> bool:
        """
        Return ``True`` if this pattern is unifiable with the pattern ``p``.
        In other words, return ``True`` if this pattern "matches" ``p``.
        """
        try:
            self.unify(p)
        except PatternError:
            return False
        else:
            return True

    def __hash__(self) -> int:
        return hash((type(self), self.params))

    def __eq__(self, other: Any) -> bool:
        return self.equal(other)

    def __repr__(self) -> str:
        params_repr = ", ".join(repr(p) for p in self.params)
        if params_repr:
            params_repr = f"[{params_repr}]"

        return f"{type(self).__name__}{params_repr}"


class Var:
    __slots__ = ("name", "predicate")

    def __init__(
        self, name: str, predicate: Optional[Callable[[Any], bool]] = None
    ) -> None:
        self.name = name
        self.predicate = predicate

    def __eq__(self, other: Any) -> bool:
        return (
            type(self) is type(other)
            and self.name == other.name
            and self.predicate is other.predicate
        )

    def __hash__(self) -> int:
        return hash((type(self), self.name, self.predicate))

    def __repr__(self) -> str:
        return self.name


T = Var("T")
U = Var("U")
V = Var("V")
W = Var("W")


Substitutions = Dict[Var, Any]


def unify(lhs: Any, rhs: Any) -> Substitutions:
    """
    Return a dictionary of substitutions such that, when all substitutions are
    performed for bound variables, the two expressions ``x`` and ``y`` become
    equivalent i.e. are unified.  Uses the Martelli-Montanari unification
    algorithm.

    References:
    - https://en.wikipedia.org/wiki/Unification_(computer_science)#A_unification_algorithm  # noqa: E501
    - https://stackoverflow.com/a/49114348/751533
    """
    equations = deque([(lhs, rhs)])
    rule_misses = 0

    while len(equations) > rule_misses:
        x, y = equations.popleft()

        if x == y:
            # delete rule
            rule_misses = 0

        elif isinstance(x, Pattern) and isinstance(y, Pattern):
            if type(x) is not type(y):
                # conflict rule (part 1)
                raise PatternError(
                    f"type mismatch: expected {type(x).__name__}, "
                    + f"got {type(y).__name__}"
                )
            else:
                # decompose rule
                for a, b in zip(x.params, y.params):
                    equations.append((a, b))
                rule_misses = 0

        elif not isinstance(x, Var) and not isinstance(y, Var):
            # conflict rule (part 2)
            # we already know x != y because the first if branch was not taken
            raise PatternError(f"concrete mismatch: expected {x}, got {y}")

        elif not isinstance(x, Var) and isinstance(y, Var):
            # swap rule
            equations.append((y, x))
            rule_misses = 0

        elif isinstance(x, Var):
            # eliminate rule
            if occurs_check(x, y):
                # check rule
                raise PatternError(
                    f"substituting {y} for {x} would cause recursive self reference"
                )
            elif x.predicate is not None and not x.predicate(y):
                raise PatternError(f"{y} did not satisfy predicate for {x}")
            elif occurs_check(x, equations):
                equations = apply_sub(x, y, equations)
                equations.append((x, y))
                rule_misses = 0
            else:
                # add rule back to queue since no rules applied
                equations.append((x, y))
                rule_misses += 1

        else:
            # By the time we reach this branch, the following must be true:
            # (x == var or y == var) and (x == var or y != var) and (x != var)
            #
            # Distributing the third clause over the second gives:
            # (x == var or y == var) and (x == var and x != var or y != var and x != var)  # noqa: E501
            #
            # Replacing the contradiction in second clause with the constant
            # `False` predicate gives:
            # (x == var or y == var) and (False or y != var and x != var)
            #
            # Simplifying the second clause by eliminating the disjunction with
            # a constant `False` operand gives:
            # (x == var or y == var) and (y != var and x != var)
            #
            # Assuming the second clause makes the first clause contradictory.
            # Therefore, this branch is unreachable.
            raise Exception("invariant")  # pragma: nocover

    return dict(equations)


def apply_sub(v: Var, x: Any, term: Any) -> Any:
    """
    Substitute ``x`` for occurences of ``v`` in ``term``.
    """
    if isinstance(term, Var):
        if term == v:
            return x
        else:
            return term
    elif isinstance(term, (list, tuple, deque)):
        return type(term)(apply_sub(v, x, i) for i in term)
    elif isinstance(term, dict):
        return {k: apply_sub(v, x, v) for k, v in term.items()}
    elif isinstance(term, Pattern):
        return type(term)(
            *(apply_sub(v, x, p) for p in term.params),
            **{n: getattr(term, n) for n in term.annotations},
        )
    else:
        return term


def occurs_check(v: Var, term: Any) -> bool:
    """
    Return ``True`` if the variable ``v`` occurs somewhere in ``term``.
    """
    if v == term:
        return True
    elif isinstance(term, (list, tuple, deque)):
        return any(occurs_check(v, i) for i in term)
    elif isinstance(term, dict):
        return any(occurs_check(v, i) for i in term.values())
    elif isinstance(term, Pattern):
        return any(occurs_check(v, p) for p in term.params)
    else:
        return False
