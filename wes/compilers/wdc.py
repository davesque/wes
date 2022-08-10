from __future__ import annotations

from enum import Enum
from typing import Dict, Iterator, Tuple, Optional

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

    op_codes: Dict[Optional[Tuple[Format, int]], int] = {
        # (arg format, arg byte length): opcode,
        # ...
    }

    def validate(self) -> None:
        n_args = len(self.op.args)

        if n_args == 0:
            try:
                op_code = self.op_codes[None]
            except KeyError:
                raise Message(
                    f"instruction '{self.mnemonic}' expects an argument", self.op.toks
                )

            self._op_code = op_code
            self._le_bytes = ()
            self._size = 1

        elif n_args == 1:
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

        else:
            raise Message(
                f"instruction '{self.mnemonic}' expects one argument", self.op.toks
            )

    def encode(self) -> Iterator[int]:
        yield self._op_code
        yield from self._le_bytes

    @property
    def size(self) -> int:
        return self._size


class RelativeUnary(Unary):
    __slots__ = ("_evaled",)  # type: ignore

    op_code: int = None  # type: ignore
    size = 2  # type: ignore

    def validate(self) -> None:
        n_args = len(self.op.args)

        if n_args == 0:
            raise Message(
                f"instruction '{self.mnemonic}' expects an argument", self.op.toks
            )
        elif n_args == 1:
            arg = self.op.args[0]
            evaled = arg.eval(self.compiler.scope)

            b_len = byte_length(evaled)
            if b_len > 1:
                raise Message(
                    f"evaluated result '{evaled}' does not fit in one byte", arg.toks
                )

            self._evaled = evaled
        else:
            raise Message(
                f"instruction '{self.mnemonic}' expects one argument", self.op.toks
            )

    def encode(self) -> Iterator[int]:
        yield self.op_code
        yield self._evaled


class Nop(Constant):
    mnemonic = "nop"
    output = 0xEA


class Adc(WdcUnary):
    mnemonic = "adc"

    op_codes = {
        (Format.DIR, 2): 0x6D,
        (Format.IDX_X, 2): 0x7D,
        (Format.IDX_Y, 2): 0x79,
        (Format.IMM, 1): 0x69,
        (Format.DIR, 1): 0x65,
        (Format.IDX_IND, 1): 0x61,
        (Format.IDX_X, 1): 0x75,
        (Format.IND, 1): 0x72,
        (Format.IND_Y, 1): 0x71,
    }


class And(WdcUnary):
    mnemonic = "and"

    op_codes = {
        (Format.DIR, 2): 0x2D,
        (Format.IDX_X, 2): 0x3D,
        (Format.IDX_Y, 2): 0x39,
        (Format.IMM, 1): 0x29,
        (Format.DIR, 1): 0x25,
        (Format.IDX_IND, 1): 0x21,
        (Format.IDX_X, 1): 0x35,
        (Format.IND, 1): 0x32,
        (Format.IND_Y, 1): 0x31,
    }


class Asl(WdcUnary):
    mnemonic = "asl"

    op_codes = {
        (Format.DIR, 2): 0x0E,
        (Format.IDX_X, 2): 0x1E,
        None: 0x0A,
        (Format.DIR, 1): 0x06,
        (Format.IDX_X, 1): 0x16,
    }


class Bbr0(RelativeUnary):
    mnemonic = "bbr0"
    op_code = 0x0F


class Bbr1(RelativeUnary):
    mnemonic = "bbr1"
    op_code = 0x1F


class Bbr2(RelativeUnary):
    mnemonic = "bbr2"
    op_code = 0x2F


class Bbr3(RelativeUnary):
    mnemonic = "bbr3"
    op_code = 0x3F


class Bbr4(RelativeUnary):
    mnemonic = "bbr4"
    op_code = 0x4F


class Bbr5(RelativeUnary):
    mnemonic = "bbr5"
    op_code = 0x5F


class Bbr6(RelativeUnary):
    mnemonic = "bbr6"
    op_code = 0x6F


class Bbr7(RelativeUnary):
    mnemonic = "bbr7"
    op_code = 0x7F


class Bbs0(RelativeUnary):
    mnemonic = "bbs0"
    op_code = 0x8F


class Bbs1(RelativeUnary):
    mnemonic = "bbs1"
    op_code = 0x9F


class Bbs2(RelativeUnary):
    mnemonic = "bbs2"
    op_code = 0xAF


class Bbs3(RelativeUnary):
    mnemonic = "bbs3"
    op_code = 0xBF


class Bbs4(RelativeUnary):
    mnemonic = "bbs4"
    op_code = 0xCF


class Bbs5(RelativeUnary):
    mnemonic = "bbs5"
    op_code = 0xDF


class Bbs6(RelativeUnary):
    mnemonic = "bbs6"
    op_code = 0xEF


class Bbs7(RelativeUnary):
    mnemonic = "bbs7"
    op_code = 0xFF


class Bcc(RelativeUnary):
    mnemonic = "bcc"
    op_code = 0x90


class Bcs(RelativeUnary):
    mnemonic = "bcs"
    op_code = 0xB0


class Beq(RelativeUnary):
    mnemonic = "beq"
    op_code = 0xF0


class Lda(WdcUnary):
    mnemonic = "lda"

    op_codes = {
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

    op_codes = {
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
        Adc.mnemonic: Adc,
        And.mnemonic: And,
        Asl.mnemonic: Asl,
        Bbr0.mnemonic: Bbr0,
        Bbr1.mnemonic: Bbr1,
        Bbr2.mnemonic: Bbr2,
        Bbr3.mnemonic: Bbr3,
        Bbr4.mnemonic: Bbr4,
        Bbr5.mnemonic: Bbr5,
        Bbr6.mnemonic: Bbr6,
        Bbr7.mnemonic: Bbr7,
        Bbs0.mnemonic: Bbs0,
        Bbs1.mnemonic: Bbs1,
        Bbs2.mnemonic: Bbs2,
        Bbs3.mnemonic: Bbs3,
        Bbs4.mnemonic: Bbs4,
        Bbs5.mnemonic: Bbs5,
        Bbs6.mnemonic: Bbs6,
        Bbs7.mnemonic: Bbs7,
        Bcc.mnemonic: Bcc,
        Bcs.mnemonic: Bcs,
        Beq.mnemonic: Beq,
        Nop.mnemonic: Nop,
        Lda.mnemonic: Lda,
        Ldx.mnemonic: Ldx,
    }
