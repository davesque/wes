import argparse
import shutil
import sys
from io import StringIO
from typing import Callable, TextIO

from wes.compiler import Compiler
from wes.compilers.sap import SapCompiler
from wes.exceptions import Message, Stop

Formatter = Callable[[Compiler], None]


def binary_text(compiler: Compiler) -> None:
    for i, code in enumerate(compiler):
        print(f"{i:04b}: {code >> 4:04b} {code & 15:04b}", file=sys.stdout)


class ReadCompiler:
    def __init__(self, compiler: Compiler):
        self.it = iter(compiler)

    def read(self, n: int = -1) -> bytes:
        bs = []

        if n == -1:
            try:
                while True:
                    bs.append(next(self.it))
            except StopIteration:
                pass
        else:
            try:
                for _ in range(n):
                    bs.append(next(self.it))
            except StopIteration:
                pass

        return bytes(bs)


def binary(compiler: Compiler) -> None:
    shutil.copyfileobj(ReadCompiler(compiler), sys.stdout.buffer)


def run(in_buf: TextIO, formatter: Formatter) -> None:
    try:
        compiler = SapCompiler.from_buf(in_buf)
    except Stop as e:
        raise Message(e.msg, e.toks)

    formatter(compiler)


FORMATTERS = {
    "binary_text": binary_text,
    "binary": binary,
}

parser = argparse.ArgumentParser(description="Compile an assembly file.")
parser.add_argument(
    "file",
    nargs="?",
    type=argparse.FileType("r"),
    help="path to program file",
    default=sys.stdin,
)
parser.add_argument(
    "-f",
    "--format",
    help="format of compiled output",
    default="binary_text",
    choices=FORMATTERS.keys(),
    required=False,
)


def main():  # pragma: no cover
    args = parser.parse_args()

    formatter = FORMATTERS[args.format]

    file_txt = args.file.read()
    in_buf = StringIO(file_txt)

    try:
        run(in_buf, formatter)
    except Message as e:
        print(e.render(file_txt), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
