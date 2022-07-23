from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from das.exceptions import RenderedError
from das.parser import Op

if TYPE_CHECKING:  # pragma: no cover
    from das.compiler import Compiler


class Instruction:
    mnemonic: str = None  # type: ignore

    __slots__ = ("compiler", "op")

    compiler: Compiler
    op: Op

    def __init__(self, compiler: Compiler, op: Op):
        self.compiler = compiler
        self.op = op

        self.validate()

    def validate(self) -> None:  # pragma: no cover
        raise NotImplementedError("must define `validate`")

    def encode(self) -> Iterator[int]:  # pragma: no cover
        raise NotImplementedError("must define `encode`")


class Nullary(Instruction):
    def validate(self) -> None:
        if self.op.arg is not None:
            raise RenderedError(
                f"'{self.mnemonic}' instruction takes no argument",
                self.op.toks,
            )


class Unary(Instruction):
    def validate(self) -> None:
        if self.op.arg is None:
            raise RenderedError(
                f"'{self.mnemonic}' instruction requires an argument",
                self.op.toks,
            )


class Const(Nullary):
    output: int = None  # type: ignore

    def encode(self) -> Iterator[int]:
        yield self.output
