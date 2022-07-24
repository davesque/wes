from __future__ import annotations

from typing import Dict, Iterator, TextIO, Type, TypeVar, overload

from das.exceptions import RenderedError
from das.instruction import Instruction, Value
from das.lexer import Text
from das.parser import File, Label, Op, Parser, Val

T = TypeVar("T")


class Compiler:
    max_addr = 2**64 - 1
    max_val = 2**64 - 1

    instructions: Dict[str, Type[Instruction]] = None  # type: ignore

    file: File
    labels: Dict[str, int]

    def __init__(self, file: File):
        self.file = file
        self.labels = {}

    @classmethod
    def from_str(cls: Type[T], text: str) -> T:
        parser = Parser.from_str(text)
        file = parser.parse_file()

        return cls(file)

    @classmethod
    def from_buf(cls: Type[T], buf: TextIO) -> T:
        parser = Parser.from_buf(buf)
        file = parser.parse_file()

        return cls(file)

    @overload
    def get_instruction(self, stmt: Val) -> Value:  # pragma: no cover
        ...

    @overload
    def get_instruction(self, stmt: Op) -> Instruction:  # pragma: no cover
        ...

    def get_instruction(self, stmt):
        if isinstance(stmt, Op):
            try:
                instruction_cls = self.instructions[stmt.mnemonic]
            except KeyError:
                raise RenderedError(
                    f"unrecognized instruction '{stmt.mnemonic}'", stmt.toks[0]
                )
            return instruction_cls(self, stmt)
        elif isinstance(stmt, Val):
            return Value(self, stmt)
        else:  # pragma: no cover
            raise Exception("invariant")

    def find_labels(self) -> None:
        loc = 0
        for stmt in self.file.stmts:
            if isinstance(stmt, Label):
                if stmt.name in self.labels:
                    raise RenderedError(
                        f"redefinition of label '{stmt.name}'", stmt.toks[0]
                    )

                self.labels[stmt.name] = loc
            elif isinstance(stmt, (Op, Val)):
                inst = self.get_instruction(stmt)
                loc += inst.size

                if loc > self.max_addr:
                    raise RenderedError(
                        "statement makes program too large", stmt.toks[0]
                    )
            else:  # pragma: no cover
                raise Exception("invariant")

    def resolve_label(self, label: str, label_tok: Text) -> int:
        try:
            return self.labels[label]
        except KeyError:
            raise RenderedError(f"unrecognized label '{label}'", label_tok)

    def __iter__(self) -> Iterator[int]:
        self.find_labels()

        for stmt in self.file.stmts:
            if isinstance(stmt, (Op, Val)):
                # only ops and vals generate code
                inst = self.get_instruction(stmt)
                yield from inst.encode()
