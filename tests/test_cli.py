from io import BytesIO, StringIO

import pytest

from wes.cli import Binary, BinaryText, run
from wes.compilers.sap import CompileSap
from wes.exceptions import Message


@pytest.fixture
def in_buf() -> StringIO:
    return StringIO(
        """
; Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 1
; before halting

lda init

count_up:
  out
  add incr
  jc count_down  ; jump to "count_down" if we overflowed
  jmp count_up

count_down:
  out
  sub incr
  jz end         ; jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
"""
    )


def test_run_binary_text(in_buf: StringIO) -> None:
    out_buf = StringIO()
    formatter = BinaryText(out_buf)

    run(in_buf, formatter, CompileSap)
    out_buf.seek(0)

    # fmt: off
    assert out_buf.read() == """
0000: 0001 1010
0001: 1110 0000
0010: 0010 1011
0011: 0111 0101
0100: 0110 0001
0101: 1110 0000
0110: 0011 1011
0111: 1000 1001
1000: 0110 0101
1001: 1111 0000
1010: 0010 1010
1011: 0000 0001
"""[1:]
    # fmt: on


def test_run_binary(in_buf: StringIO) -> None:
    out_buf = BytesIO()
    formatter = Binary(out_buf)

    run(in_buf, formatter, CompileSap)
    out_buf.seek(0)

    assert out_buf.read() == bytes(
        [
            0b00011010,
            0b11100000,
            0b00101011,
            0b01110101,
            0b01100001,
            0b11100000,
            0b00111011,
            0b10001001,
            0b01100101,
            0b11110000,
            0b00101010,
            0b00000001,
        ]
    )


def test_run_stop_as_message() -> None:
    in_buf = StringIO("lda init foo bar")
    formatter = BinaryText(StringIO())

    with pytest.raises(Message):
        run(in_buf, formatter, CompileSap)
