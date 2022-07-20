import sys
from typing import TextIO

from .compiler import Compiler
from .exceptions import RenderedError
from .lexer import Lexer
from .parser import Parser


def run(in_buf: TextIO, out_buf: TextIO) -> None:
    lexer = Lexer(in_buf)
    parser = Parser(lexer)

    file = parser.parse_file()
    compiler = Compiler(file)

    for i, code in enumerate(compiler):
        print(f"{i:04b}: {code >> 4:04b} {code & 15:04b}", file=out_buf)


def main():  # pragma: no cover
    try:
        if len(sys.argv) == 1:
            run(sys.stdin, sys.stdout)
        else:
            if sys.argv[1] == "-h":
                sys.stderr.write("usage: das <filename> | das < <filename>\n")
                sys.exit(1)

            with open(sys.argv[1], "r") as f:
                run(f, sys.stdout)
    except RenderedError as e:
        print(e.render(), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
