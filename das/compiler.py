from __future__ import annotations

from typing import Dict, TextIO, TypeVar, Type

from .exceptions import RenderedError
from .parser import File, Label, Parser


T = TypeVar("T")


class Compiler:
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
