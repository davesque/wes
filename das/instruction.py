from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

from das.exceptions import Message
from das.parser import Op, Val
from das.utils import byte_length

if TYPE_CHECKING:  # pragma: no cover
    from das.compiler import Compiler


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
                f"value '{self.val.toks[0].text}' is too large", (self.val.toks[0],)
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


class Const(Nullary):
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
        if isinstance(arg, str):
            resolved = self.compiler.resolve_label(arg, self.op.toks[1])
        else:
            resolved = arg

        if resolved > MAX_WORD:
            if isinstance(arg, str):
                msg = (
                    f"arg '{arg}' of instruction '{self.mnemonic}' "
                    + f"resolves to value '{resolved}' which does not fit in two bytes"
                )
            else:
                msg = (
                    f"arg '{arg}' of instruction '{self.mnemonic}' does not fit "
                    + "in two bytes"
                )
            raise Message(msg, self.op.toks)

        yield resolved & 0xFF
        yield (resolved >> 8) & 0xFF

    @property
    def size(self) -> int:
        return 2
