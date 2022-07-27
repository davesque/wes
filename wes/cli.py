import sys
from io import StringIO
from typing import TextIO

from wes.compilers.sap import SapCompiler
from wes.exceptions import Message, Stop


def run(in_buf: TextIO, out_buf: TextIO) -> None:
    try:
        compiler = SapCompiler.from_buf(in_buf)
    except Stop as e:
        raise Message(e.msg, e.toks)

    for i, code in enumerate(compiler):
        print(f"{i:04b}: {code >> 4:04b} {code & 15:04b}", file=out_buf)


def main():  # pragma: no cover
    if len(sys.argv) == 1:
        file_txt = sys.stdin.read()
        in_buf = StringIO(file_txt)
    else:
        if sys.argv[1] == "-h":
            sys.stderr.write("usage: wes <filename> | wes < <filename>\n")
            sys.exit(1)

        with open(sys.argv[1], "r") as f:
            file_txt = f.read()
        in_buf = StringIO(file_txt)

    try:
        run(in_buf, sys.stdout)
    except Message as e:
        print(e.render(file_txt), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
