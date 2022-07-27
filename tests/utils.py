import re
from typing import Callable


PredFn = Callable[[str], bool]


class Predicate:
    def __call__(self, _: str) -> bool:
        raise NotImplementedError("must implement `__call__`")

    def __repr__(self) -> str:
        raise NotImplementedError("must implement `__repr__`")


class Eq(Predicate):
    x: str

    def __init__(self, x: str):
        self.x = x

    def __call__(self, y: str) -> bool:
        return self.x == y

    def __repr__(self) -> str:
        return f"'{self.x}' == _"


class In(Predicate):
    x: str

    def __init__(self, x: str):
        self.x = x

    def __call__(self, y: str) -> bool:
        return self.x in y

    def __repr__(self) -> str:
        return f"'{self.x}' in _"


class Re(Predicate):
    pat: str
    pat_re: re.Pattern[str]

    def __init__(self, pat: str):
        self.pat = pat
        self.pat_re = re.compile(pat)

    def __call__(self, y: str) -> bool:
        return bool(self.pat_re.match(y))

    def __repr__(self) -> str:
        return f"re.compile('{self.pat}').match(_)"
