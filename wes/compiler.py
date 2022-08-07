from __future__ import annotations

from typing import Dict, Iterator, TextIO, Type, TypeVar, cast, overload

from wes.exceptions import Message
from wes.instruction import Instruction, Operation, Value
from wes.lexer import Text
from wes.parser import Expr, File, Label, Name, Offset, Op, Parser, Val

T = TypeVar("T")


class Compiler:
    max_addr = 2**64 - 1
    max_val = 2**64 - 1

    instructions: Dict[str, Type[Operation]] = {}

    file: File
    labels: Dict[str, int]
    consts: Dict[str, int]

    def __init__(self, file: File):
        self.file = file
        self.labels = {}
        self.consts = {}

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
    def get_instruction(self, stmt: Op) -> Operation:  # pragma: no cover
        ...

    def get_instruction(self, stmt):
        if isinstance(stmt, Op):
            try:
                instruction_cls = self.instructions[stmt.mnemonic]
            except KeyError:
                raise Message(
                    f"unrecognized instruction '{stmt.mnemonic}'", (stmt.toks[0],)
                )
            return instruction_cls(self, stmt)
        elif isinstance(stmt, Val):
            return Value(self, stmt)
        else:  # pragma: no cover
            raise Exception("invariant")

    def scan(self) -> None:
        last_inst = None
        loc = 0

        for stmt in self.file.stmts:
            if isinstance(stmt, Label):
                if stmt.name in self.instructions:
                    raise Message(
                        f"label '{stmt.name}' uses reserved name", (stmt.toks[0],)
                    )
                if stmt.name in self.labels:
                    raise Message(
                        f"redefinition of label '{stmt.name}'", (stmt.toks[0],)
                    )

                self.labels[stmt.name] = loc

            elif isinstance(stmt, Offset):
                offset_loc = self.resolve_offset(loc, stmt)

                if last_inst is None:
                    raise Message(
                        "offset must follow generated code usable as padding",
                        stmt.toks,
                    )

                padding_len = offset_loc - loc
                if padding_len % last_inst.size != 0:
                    # The only other instruction type this could be would be a
                    # value.  But values have size 1.  Therefore, `padding_len
                    # % last_inst.size != 0` can never be true for values.
                    if isinstance(last_inst, Operation):
                        raise Message(
                            f"size of padding instruction '{last_inst.mnemonic}' "
                            + "is not a divisor of padding length",
                            stmt.toks,
                        )
                    else:  # pragma: no cover
                        raise Exception("invariant")

                loc = offset_loc

            elif isinstance(stmt, (Op, Expr)):
                if loc > self.max_addr:
                    raise Message("statement makes program too large", (stmt.toks[0],))

                if isinstance(stmt, Name):
                    # rewrite free standing names as nullary ops
                    stmt = Op(stmt.name, (), toks=stmt.toks)
                elif isinstance(stmt, Expr):
                    # rewrite any other expression as a literal value after
                    # evaluation
                    stmt = Val(stmt.eval(self.labels), toks=stmt.toks)

                last_inst = self.get_instruction(stmt)
                loc += last_inst.size

            else:  # pragma: no cover
                raise Exception("invariant")

    def resolve_label(self, label: str, label_tok: Text) -> int:
        try:
            return self.labels[label]
        except KeyError:
            raise Message(f"unrecognized label '{label}'", (label_tok,))

    def resolve_offset(self, loc: int, offset: Offset) -> int:
        if offset.relative == "+":
            # offset moves forward from current loc
            offset_loc = loc + offset.offset
        elif offset.relative == "-":
            # offset moves back from end of address space
            offset_loc = self.max_addr - offset.offset + 1
        else:
            # offset is absolute
            offset_loc = offset.offset

        if offset_loc > self.max_addr:
            raise Message(
                f"offset resolves to oversized location '{offset_loc}'",
                offset.toks[:-1],
            )
        if offset_loc < loc:
            raise Message(
                f"offset resolves to location '{offset_loc}' before current position",
                offset.toks[:-1],
            )

        return offset_loc

    def __iter__(self) -> Iterator[int]:
        self.scan()

        last_inst = None
        loc = 0

        for stmt in self.file.stmts:
            if isinstance(stmt, (Op, Expr)):
                if isinstance(stmt, Name):
                    # rewrite free standing names as nullary ops
                    stmt = Op(stmt.name, (), toks=stmt.toks)
                elif isinstance(stmt, Expr):
                    # rewrite any other expression as a literal value after
                    # evaluation
                    stmt = Val(stmt.eval(self.labels), toks=stmt.toks)

                last_inst = self.get_instruction(stmt)
                yield from last_inst.encode()

                loc += last_inst.size

            elif isinstance(stmt, Offset):
                offset_loc = self.resolve_offset(loc, stmt)

                # We know this from the `scan` pass.  Scan will throw an error
                # if an offset is not preceded by a padding instruction.
                last_inst = cast(Instruction, last_inst)

                padding_len = offset_loc - loc
                output_len = 0
                for _ in range(padding_len // last_inst.size):
                    yield from last_inst.encode()
                    output_len += last_inst.size

                if padding_len != output_len:  # pragma: no cover
                    Exception("invariant")

                loc = offset_loc
