from typing import Iterator

from das.compiler import Compiler
from das.exceptions import RenderedError
from das.instruction import Const, Unary


class SapUnary(Unary):
    code: int = None  # type: ignore

    def encode(self) -> Iterator[int]:
        if isinstance(self.op.arg, str):
            arg = self.compiler.resolve_label(self.op.arg, self.op.toks[1])
        elif isinstance(self.op.arg, int):
            if self.op.arg > self.compiler.max_addr:
                raise RenderedError(
                    f"arg '{self.op.arg}' is too large",
                    self.op.toks[1],
                )
            arg = self.op.arg
        else:  # pragma: no cover
            raise Exception("invariant")

        yield (self.code << 4) + arg


class Nop(Const):
    mnemonic = "nop"
    output = 0b00000000


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


class Out(Const):
    mnemonic = "out"
    output = 0b11100000


class Hlt(Const):
    mnemonic = "hlt"
    output = 0b11110000


class SapCompiler(Compiler):
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
