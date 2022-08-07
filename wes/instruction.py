from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from wes.exceptions import Message
from wes.parser import Op, Val
from wes.utils import byte_length

if TYPE_CHECKING:  # pragma: no cover
    from wes.compiler import Compiler


class Instruction:
    __slots__ = ("compiler",)

    compiler: Compiler

    def __init__(self, compiler: Compiler):
        self.compiler = compiler
        self.validate()

    def validate(self) -> None:  # pragma: no cover
        raise NotImplementedError("must define `validate`")

    def encode(self) -> Iterator[int]:  # pragma: no cover
        raise NotImplementedError("must define `encode`")

    @property
    def size(self) -> int:  # pragma: no cover
        raise NotImplementedError("must define `size`")


class Operation(Instruction):
    __slots__ = ("op",)

    mnemonic: str = None  # type: ignore
    op: Op

    def __init__(self, compiler: Compiler, op: Op):
        self.op = op
        super().__init__(compiler)


class Value(Instruction):
    __slots__ = ("val",)

    val: Val

    def __init__(self, compiler: Compiler, val: Val):
        self.val = val
        super().__init__(compiler)

    def validate(self) -> None:
        if self.val.val > self.compiler.max_val:
            raise Message(
                f"evaluated result '{self.val.val}' is too large", self.val.toks
            )

    def encode(self) -> Iterator[int]:
        yield self.val.val

    @property
    def size(self) -> int:
        return byte_length(self.val.val)


class Nullary(Operation):
    def validate(self) -> None:
        if len(self.op.args) > 0:
            raise Message(
                f"'{self.mnemonic}' instruction takes no argument",
                self.op.toks,
            )


class Unary(Operation):
    def validate(self) -> None:
        if len(self.op.args) != 1:
            raise Message(
                f"'{self.mnemonic}' instruction takes one argument",
                self.op.toks,
            )


class Constant(Nullary):
    output: int = None  # type: ignore

    def encode(self) -> Iterator[int]:
        yield self.output

    @property
    def size(self) -> int:
        return byte_length(self.output)


MAX_WORD = 2**16 - 1


class Word(Unary):
    mnemonic = "word"

    def encode(self) -> Iterator[int]:
        arg = self.op.args[0]
        evaled = arg.eval(self.compiler.labels)

        if evaled > MAX_WORD:
            raise Message(
                f"evaluated result '{evaled}' does not fit in two bytes", arg.toks
            )

        yield evaled & 0xFF
        yield (evaled >> 8) & 0xFF

    @property
    def size(self) -> int:
        return 2
