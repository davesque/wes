from io import StringIO

from das.compiler import Compiler
from das.lexer import Lexer
from das.parser import Parser


def test_compile_count() -> None:
    buf = StringIO(
        """
# Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
# before halting

lda init

count_up:
  out
  add incr
  jc count_down  # jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         # jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()
    compiler = Compiler(file)

    assert list(compiler) == [26, 224, 43, 117, 97, 224, 59, 137, 101, 240, 42, 1]


def test_compile_fib() -> None:
    buf = StringIO(
        """
# Counts up in fibonacci numbers forever (with a lot of overflow)

loop:
  lda a
  out
  add b
  sta a

  lda b
  out
  add a
  sta b

  jmp loop

a: 1
b: 1
"""
    )
    lexer = Lexer(buf)
    parser = Parser(lexer)
    file = parser.parse_file()
    compiler = Compiler(file)

    assert list(compiler) == [25, 224, 42, 73, 26, 224, 41, 74, 96, 1, 1]
