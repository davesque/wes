import argparse
import shutil
import sys
from io import StringIO
from typing import BinaryIO, Generic, TextIO, Type, TypeVar

from wes.compiler import Compiler
from wes.compilers.sap import CompileSap
from wes.compilers.wdc import Compile6502
from wes.exceptions import Message, Stop

IoType = TypeVar("IoType", TextIO, BinaryIO)


class Formatter(Generic[IoType]):
    buf: IoType

    def __init__(self, buf: IoType):
        self.buf = buf

    def format(self, compiler: Compiler) -> None:  # pragma: no cover
        raise NotImplementedError("must implement `format`")


class BinaryText(Formatter[TextIO]):
    def format(self, compiler: Compiler) -> None:
        for i, code in enumerate(compiler):
            print(f"{i:04b}: {code >> 4:04b} {code & 15:04b}", file=self.buf)


class ReadCompiler:
    def __init__(self, compiler: Compiler):
        self.it = iter(compiler)

    def read(self, n: int = -1) -> bytes:
        bs = []

        try:
            if n == -1:
                while True:  # pragma: no cover
                    bs.append(next(self.it))
            else:
                for _ in range(n):
                    bs.append(next(self.it))
        except StopIteration:
            pass

        return bytes(bs)


class Binary(Formatter[BinaryIO]):
    def format(self, compiler: Compiler) -> None:
        shutil.copyfileobj(ReadCompiler(compiler), self.buf)


def run(
    in_buf: TextIO, formatter: Formatter[IoType], compiler_cls: Type[Compiler]
) -> None:
    try:
        compiler = compiler_cls.from_buf(in_buf)
    except Stop as e:
        raise Message(e.msg, e.toks)

    formatter.format(compiler)


FORMATTERS = {
    "binary": Binary(sys.stdout.buffer),
    "binary_text": BinaryText(sys.stdout),
}
COMPILERS = {
    "sap1": CompileSap,
    "w65c02s": Compile6502,
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
    default="binary",
    choices=FORMATTERS.keys(),
    required=False,
)
parser.add_argument(
    "-a",
    "--arch",
    help="target architecture",
    default="w65c02s",
    choices=COMPILERS.keys(),
    required=False,
)


def main():  # pragma: no cover
    args = parser.parse_args()

    formatter = FORMATTERS[args.format]
    compiler_cls = COMPILERS[args.arch]

    file_txt = args.file.read()
    in_buf = StringIO(file_txt)

    try:
        run(in_buf, formatter, compiler_cls)
    except Message as e:
        print(e.render(file_txt), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()
