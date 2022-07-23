from typing import Iterator

from das.compiler import Compiler
from das.exceptions import RenderedError
from das.parser import Op, Val


class Instruction:
    mnemonic: str = None  # type: ignore

    __slots__ = ("compiler", "op")

    compiler: Compiler
    op: Op

    def __init__(self, compiler: Compiler, op: Op):
        self.compiler = compiler
        self.op = op

        self.validate()

    def validate(self) -> None:
        raise NotImplementedError("must define `validate`")

    def __iter__(self) -> Iterator[int]:
        raise NotImplementedError("must define `__iter__`")


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


class SapUnary(Unary):
    code: int = None  # type: ignore

    def __iter__(self) -> Iterator[int]:
        if isinstance(self.op.arg, str):
            loc = self.compiler.resolve_label(self.op.arg, self.op.toks[1])
            yield (self.code << 4) + loc

        elif isinstance(self.op.arg, int):
            if self.op.arg > self.compiler.max_addr:
                raise RenderedError(
                    f"arg '{self.op.arg}' is too large", self.op.toks[1]
                )

            yield (self.code << 4) + self.op.arg

        else:
            raise Exception("invariant")


class Const(Nullary):
    output: int = None  # type: ignore

    def __iter__(self) -> Iterator[int]:
        yield self.output


class Nop(Const):
    mnemonic = "nop"
    output = 0b00000000


class Out(Const):
    mnemonic = "out"
    output = 0b11100000


class Hlt(Const):
    mnemonic = "hlt"
    output = 0b11110000


class Lda(SapUnary):
    mnemonic = "lda"
    code = 0b0001


class Add(SapUnary):
    mnemonic = "add"
    code = 0b0010


class Sub(SapUnary):
    mnemonic = "sub"
    code = 0b0011


class Sta(SapUnary):
    mnemonic = "sta"
    code = 0b0100


class Ldi(SapUnary):
    mnemonic = "ldi"
    code = 0b0101


class Jmp(SapUnary):
    mnemonic = "jmp"
    code = 0b0110


class Jc(SapUnary):
    mnemonic = "jc"
    code = 0b0111


class Jz(SapUnary):
    mnemonic = "jz"
    code = 0b1000


class Sap1(Compiler):
    max_addr = 15
    max_val = 255

    instructions = {
        Nop.mnemonic: Nop,
        Lda.mnemonic: Lda,
        Add.mnemonic: Add,
        Sub.mnemonic: Sub,
        Sta.mnemonic: Sta,
        Ldi.mnemonic: Ldi,
        Jmp.mnemonic: Jmp,
        Jc.mnemonic: Jc,
        Jz.mnemonic: Jz,
        Out.mnemonic: Out,
        Hlt.mnemonic: Hlt,
    }

    def __iter__(self) -> Iterator[int]:
        self.find_labels()

        for stmt in self.file.stmts:
            if isinstance(stmt, Op):
                try:
                    instruction_cls = self.instructions[stmt.mnemonic]
                except KeyError:
                    raise RenderedError(
                        f"unrecognized instruction '{stmt.mnemonic}'", stmt.toks
                    )

                inst = instruction_cls(self, stmt)
                yield from inst

            elif isinstance(stmt, Val):
                if stmt.val > self.max_val:
                    raise RenderedError(
                        f"value '{stmt.toks[0].text}' is too large", stmt.toks[0]
                    )

                yield stmt.val
