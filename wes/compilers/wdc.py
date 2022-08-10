from __future__ import annotations

from enum import Enum
from typing import Dict, Iterator, Tuple

from wes.compiler import Compiler
from wes.exceptions import Message, PatternError
from wes.instruction import Constant, Unary
from wes.parser import BinExpr, Deref, Expr, Name
from wes.pattern import Pattern, T
from wes.utils import byte_length, le_bytes


class Format(Enum):
    # absolute/zero-page indexed indirect -- [[... + x]]
    IDX_IND = Deref(Deref(BinExpr(T, "+", Name("x"))))

    # absolute/zero-page indirect -- [[...]]
    IND = Deref(Deref(T))

    # zero-page indirect indexed with y -- [[...] + y]
    IND_Y = Deref(BinExpr(Deref(T), "+", Name("y")))

    # absolute/zero-page indexed with x -- [... + x]
    IDX_X = Deref(BinExpr(T, "+", Name("x")))

    # absolute/zero-page indexed with y -- [... + y]
    IDX_Y = Deref(BinExpr(T, "+", Name("y")))

    # absolute/zero-page "direct" -- [...]
    DIR = Deref(T)

    # immediate (any other unmatched arg, implies non-deref)
    IMM = T

    @staticmethod
    def match(arg: Pattern) -> Tuple[Format, Expr]:
        for fmt in Format:
            try:
                subs = arg.unify(fmt.value)
            except PatternError:
                continue
            else:
                return fmt, subs[T]

        # an arg should always at least match the "immediate" format
        raise Exception("invariant")  # pragma: no cover


FORMAT_NAMES = {
    Format.DIR: "direct",
    Format.IDX_IND: "indexed indirect",
    Format.IDX_X: "indexed with x",
    Format.IDX_Y: "indexed with y",
    Format.IND: "indirect",
    Format.IND_Y: "indirect indexed with y",
    Format.IMM: "immediate",
}


class WdcUnary(Unary):
    __slots__ = ("_op_code", "_le_bytes", "_size")  # type: ignore

    op_codes: Dict[Tuple[Format, int], int] = {
        # (arg format, arg byte length): opcode,
        # ...
    }

    def validate(self) -> None:
        fmt, arg = Format.match(self.op.args[0])

        evaled = arg.eval(self.compiler.scope)

        b_len = byte_length(evaled)
        if b_len > 2:
            raise Message(
                f"evaluated result '{evaled}' does not fit in two bytes", arg.toks
            )

        try:
            op_code = self.op_codes[fmt, b_len]
        except KeyError:
            fmt_name = FORMAT_NAMES[fmt]
            raise Message(
                f"instruction '{self.mnemonic}' does not support "
                + f"addressing mode '{fmt_name}' for "
                + f"{b_len} byte operands",
                arg.toks,
            )

        self._op_code = op_code
        self._le_bytes = le_bytes(evaled, b_len)
        self._size = b_len + 1

    def encode(self) -> Iterator[int]:
        yield self._op_code
        yield from self._le_bytes

    @property
    def size(self) -> int:
        return self._size


class Nop(Constant):
    mnemonic = "nop"
    output = 0xEA


class Lda(WdcUnary):
    mnemonic = "lda"

    op_codes: Dict[Tuple[Format, int], int] = {
        (Format.DIR, 2): 0xAD,
        (Format.IDX_X, 2): 0xBD,
        (Format.IDX_Y, 2): 0xB9,
        (Format.IMM, 1): 0xA9,
        (Format.DIR, 1): 0xA5,
        (Format.IDX_IND, 1): 0xA1,
        (Format.IDX_X, 1): 0xB5,
        (Format.IND, 1): 0xB2,
        (Format.IND_Y, 1): 0xB1,
    }


class Ldx(WdcUnary):
    mnemonic = "ldx"

    op_codes: Dict[Tuple[Format, int], int] = {
        (Format.DIR, 2): 0xAE,
        (Format.IDX_Y, 2): 0xBE,
        (Format.IMM, 1): 0xA2,
        (Format.DIR, 1): 0xA6,
        (Format.IDX_Y, 1): 0xB6,
    }


class Compile6502(Compiler):
    max_addr = 2**16 - 1
    max_val = 255

    instructions = {
        Nop.mnemonic: Nop,
        Lda.mnemonic: Lda,
        Ldx.mnemonic: Ldx,
    }
