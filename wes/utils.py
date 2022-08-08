from typing import Any, Dict, Tuple

BASES = {
    "0b": 2,
    "0o": 8,
    "0x": 16,
}


def str_to_int(s: str) -> int:
    prefix = s[:2]
    base = BASES.get(prefix, 10)

    return int(s, base=base)


def byte_length(i: int) -> int:
    return max(1, (i.bit_length() + 7) // 8)


def serialize_dict(dct: Dict[str, Any]) -> Tuple[Tuple[str, Any], ...]:
    items = list(dct.items())
    items.sort(key=lambda i: i[0])

    return tuple(items)


class SlotClass:
    __slots__: Tuple[str, ...] = ()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # set parameters
        for name, param in zip(self.__slots__, args):
            setattr(self, name, param)
        for name, param in kwargs.items():
            setattr(self, name, param)

        # make sure all parameters are set
        for name in self.__slots__:
            try:
                getattr(self, name)
            except AttributeError:
                raise TypeError(
                    f"{type(self).__name__} requires a setting "
                    + f"for the '{name}' parameter"
                )
