from __future__ import annotations

from typing import Iterator, TextIO

from .exceptions import RenderedError
from .parser import File, Label, Op, Parser, Val


class Compiler:
    OPS = {
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

    def __init__(self, file: File):
        self.file = file
        self.labels = {}

    @classmethod
    def from_str(cls, text: str) -> Compiler:
        parser = Parser.from_str(text)
        file = parser.parse_file()

        return cls(file)

    @classmethod
    def from_buf(cls, buf: TextIO) -> Compiler:
        parser = Parser.from_buf(buf)
        file = parser.parse_file()

        return cls(file)

    def find_labels(self) -> None:
        loc = 0
        for stmt in self.file.stmts:
            if loc > 15:
                raise RenderedError("statement makes program too large", stmt.toks[0])

            if isinstance(stmt, Label):
                if stmt.name in self.labels:
                    raise RenderedError(
                        f"redefinition of label '{stmt.name}'", stmt.toks[0]
                    )

                self.labels[stmt.name] = loc
            else:
                loc += 1

    def __iter__(self) -> Iterator[int]:
        self.find_labels()

        for stmt in self.file.stmts:
            if isinstance(stmt, Op):
                code, arity = self.OPS[stmt.mnemonic]

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
                    if stmt.arg not in self.labels:
                        raise RenderedError(
                            f"unrecognized label '{stmt.arg}'", stmt.toks[1]
                        )

                    loc = self.labels[stmt.arg]
                    yield (code << 4) + loc
                elif isinstance(stmt.arg, int):
                    if stmt.arg > 15:
                        raise RenderedError(
                            f"arg '{stmt.arg}' is too large", stmt.toks[1]
                        )

                    yield (code << 4) + stmt.arg
                elif stmt.arg is None:
                    yield code << 4
                else:  # pragma: no cover
                    raise Exception("invariant")

            elif isinstance(stmt, Val):
                if stmt.val > 255:
                    raise RenderedError(
                        f"value '{stmt.toks[0].text}' is too large", stmt.toks[0]
                    )

                yield stmt.val
