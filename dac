#!/usr/bin/env python3

from typing import Dict, List, TextIO
from io import StringIO

import sys
import re


LABEL_RE = re.compile(r"^([a-zA-Z0-9_]+)\s*:$")
LABELED_RE = re.compile(r"^([a-zA-Z0-9_]+)\s*:\s*(.+)$")


def str_to_int(s: str) -> int:
    for base in (2, 8, 10, 16):
        try:
            return int(s, base=base)
        except ValueError:
            pass

    raise ValueError(f"string '{s}' not recognizable as integer literal")


class Program:
    labels: Dict[str, int]
    code: List[int]

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

    def __init__(self):
        self.labels = {}
        self.code = []

    def parse_code(self, code_str: str) -> int:
        parts = code_str.split(maxsplit=1)

        if len(parts) == 1:
            # maybe nullary operation
            op = code_str.lower()
            if op in self.OPS:
                code, arity = self.OPS[op]
                if arity != 0:
                    raise ValueError(f"Op '{code_str}' requires an argument.  None given.")

                return code << 4

            # maybe int literal
            try:
                return str_to_int(code_str)
            except ValueError as e:
                raise ValueError(f"String '{code_str}' not recognizable as operation or integer literal") from e

        else:
            op, arg = parts
            op = op.lower()

            if op not in self.OPS:
                raise ValueError(f"Unrecognized op '{op}'")

            code, arity = self.OPS[op]
            if arity != 1:
                raise ValueError(f"Op '{op}' expects no arguments.  Got arg '{arg}'.")

            # maybe arg is a section or data label
            if arg in self.labels:
                return (code << 4) + self.labels[arg]

            # maybe arg is int literal
            try:
                n = str_to_int(arg)
            except ValueError as e:
                raise ValueError(f"Arg '{code_str}' not recognizable as label or integer literal") from e

            return (code << 4) + n

    def validate_label(self, label: str) -> None:
        if label.lower() in self.OPS:
            raise ValueError(f"Label '{label}' uses a reserved name")

        if label in self.labels:
            raise ValueError(f"Label '{label}' defined more than once")

    def parse(self, f):
        lines = f.readlines()

        # strip out comments, empty lines, and bracketing whitespace
        lines = [l.split("#", maxsplit=1)[0] for l in lines]
        lines = [l.strip() for l in lines if l.strip()]

        # parse labels
        loc = 0
        for l in lines:
            label_match = LABEL_RE.match(l)
            labeled_match = LABELED_RE.match(l)

            if label_match is not None:
                label, = label_match.groups()
                self.validate_label(label)
                self.labels[label] = loc
                # like empty line, don't increment location

            elif labeled_match is not None:
                label, _ = labeled_match.groups()
                self.validate_label(label)
                self.labels[label] = loc
                loc += 1

            else:
                loc += 1

        # parse program
        for l in lines:
            if LABEL_RE.match(l):
                # bare labels don't generate code
                continue

            labeled_match = LABELED_RE.match(l)
            if labeled_match is not None:
                _, val = labeled_match.groups()
                self.code.append(self.parse_code(val))
            else:
                self.code.append(self.parse_code(l))

    def write(self, f: TextIO) -> None:
        for i, c in enumerate(self.code):
            f.write(f"{i:04b}: {c >> 4:04b} {c & 15:04b}\n")


if __name__ == "__main__":
    prog = Program()

    if len(sys.argv) == 1:
        prog.parse(sys.stdin)
    else:
        with open(sys.argv[1], 'r') as f:
            buf = StringIO(f.read())
        prog.parse(buf)

    prog.write(sys.stdout)
