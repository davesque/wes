from io import StringIO

from das.cli import run


def test_run() -> None:
    in_buf = StringIO(
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
    out_buf = StringIO()

    run(in_buf, out_buf)
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
