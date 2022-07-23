from typing import Iterator

from das.compiler import Compiler
from das.exceptions import RenderedError
from das.parser import Op, Val


class Sap1(Compiler):
    max_addr = 15
    max_val = 255

    ops = {
        "nop": (0b0000, 0),
        "lda": (0b0001, 1),
        "add": (0b0010, 1),
        "sub": (0b0011, 1),
        "sta": (0b0100, 1),
        "ldi": (0b0101, 1),
        "jmp": (0b0110, 1),
        "jc": (0b0111, 1),
        "jz": (0b1000, 1),
        "out": (0b1110, 0),
        "hlt": (0b1111, 0),
    }

    def __iter__(self) -> Iterator[int]:
        self.find_labels()

        for stmt in self.file.stmts:
            if isinstance(stmt, Op):
                code, arity = self.ops[stmt.mnemonic]

                if arity == 1 and stmt.arg is None:
                    raise RenderedError(
                        f"operation '{stmt.mnemonic}' requires an argument",
                        stmt.toks[0],
                    )

                if arity == 0 and stmt.arg is not None:
                    raise RenderedError(
                        f"operation '{stmt.mnemonic}' takes no argument",
                        stmt.toks[0],
                    )

                if isinstance(stmt.arg, str):
                    loc = self.resolve_label(stmt.arg, stmt.toks[1])
                    yield (code << 4) + loc
                elif isinstance(stmt.arg, int):
                    if stmt.arg > self.max_addr:
                        raise RenderedError(
                            f"arg '{stmt.arg}' is too large", stmt.toks[1]
                        )

                    yield (code << 4) + stmt.arg
                elif stmt.arg is None:
                    yield code << 4
                else:  # pragma: no cover
                    raise Exception("invariant")

            elif isinstance(stmt, Val):
                if stmt.val > self.max_val:
                    raise RenderedError(
                        f"value '{stmt.toks[0].text}' is too large", stmt.toks[0]
                    )

                yield stmt.val
