#!/usr/bin/env python3

from typing import TextIO

import sys

from .exceptions import RenderedError
from .lexer import Lexer
from .parser import Parser
from .compiler import Compiler


def run(f: TextIO, out: TextIO) -> None:
    lexer = Lexer(f)
    parser = Parser(lexer)

    try:
        file = parser.parse_file()
    except RenderedError as e:
        print(e.render(), file=sys.stderr)
        sys.exit(1)

    try:
        compiler = Compiler(file)
    except RenderedError as e:
        print(e.render(), file=sys.stderr)
        sys.exit(1)

    try:
        for i, code in enumerate(compiler):
            print(f"{i:04b}: {code >> 4:04b} {code & 15:04b}", file=out)
    except RenderedError as e:
        print(e.render(), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        run(sys.stdin, sys.stdout)
    else:
        if sys.argv[1] == "-h":
            sys.stderr.write(f"usage: das <filename> | das < <filename>\n")
            sys.exit(1)

        with open(sys.argv[1], 'r') as f:
            run(f, sys.stdout)
