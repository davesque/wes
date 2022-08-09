from enum import Enum
from typing import Dict, Iterator, Tuple

from wes.compiler import Compiler
from wes.exceptions import Message, PatternError
from wes.instruction import Constant, Unary
from wes.parser import BinExpr, Deref, Name
from wes.pattern import T
from wes.utils import byte_length, le_bytes


class Mode(Enum):
    DEREF = Deref(T)  # [T]
    IDX_IND = Deref(Deref(BinExpr(T, "+", Name("x"))))  # [[T + x]]
    IDX_X = Deref(BinExpr(T, "+", Name("x")))  # [T + x]
    IDX_Y = Deref(BinExpr(T, "+", Name("y")))  # [T + y]
    IND = Deref(T)  # [[T]]
    IND_Y = Deref(BinExpr(Deref(T), "+", Name("y")))  # [[T] + y]
    IMM = T  # T


class WdcUnary(Unary):
    __slots__ = ("_op_code", "_le_bytes", "_size")  # type: ignore

    op_codes: Dict[Tuple[Mode, int], int] = {
        # (arg format, operand byte length): opcode
    }

    def validate(self) -> None:
        arg = self.op.args[0]

        for mode in Mode:
            try:
                subs = arg.unify(mode.value)
            except PatternError:
                continue

            arg_ = subs[T]
            evaled = arg_.eval(self.compiler.scope)

            b_len = byte_length(evaled)
            if b_len > 2:
                raise Message(
                    f"evaluated result '{evaled}' does not fit in two bytes", arg_.toks
                )

            try:
                op_code = self.op_codes[mode, b_len]
            except KeyError:
                raise Message(
                    f"instruction '{self.mnemonic}' does not support "
                    + f"addressing mode '{mode.name}' for "
                    + f"{b_len} byte operand '{evaled}'",
                    arg_.toks,
                )

            self._op_code = op_code
            self._le_bytes = le_bytes(evaled, b_len)
            self._size = b_len + 1

            break

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

    op_codes: Dict[Tuple[Mode, int], int] = {
        (Mode.DEREF, 2): 0xAD,
        (Mode.IDX_X, 2): 0xBD,
        (Mode.IDX_Y, 2): 0xB9,
        (Mode.IMM, 1): 0xA9,
        (Mode.DEREF, 1): 0xA5,
        (Mode.IDX_IND, 1): 0xA1,
        (Mode.IDX_X, 1): 0xB5,
        (Mode.IND, 1): 0xB2,
        (Mode.IND_Y, 1): 0xB1,
    }


class Ldx(WdcUnary):
    mnemonic = "ldx"

    op_codes: Dict[Tuple[Mode, int], int] = {
        (Mode.DEREF, 2): 0xAE,
        (Mode.IDX_Y, 2): 0xBE,
        (Mode.IMM, 1): 0xA2,
        (Mode.DEREF, 1): 0xA6,
        (Mode.IDX_Y, 1): 0xB6,
    }


class Compile6502(Compiler):
    max_addr = 2**16 - 1
    max_val = 255

    instructions = {
        Nop.mnemonic: Nop,
        Lda.mnemonic: Lda,
    }
