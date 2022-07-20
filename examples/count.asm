# Counts from 42 to 256 (zero really in 8 bits), then down from 255 to 0
# before halting

lda init

count_up:
  add incr
  out
  jc count_down  # jump to "count_down" if we overflowed
  jmp count_up

count_down:
  sub incr
  out
  jz end         # jump to "end" if we hit zero
  jmp count_down

end: hlt

init: 42
incr: 1
