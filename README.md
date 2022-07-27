# wes, the WEird aSsembler

This is a little assembler that can be used to generate program code for Ben
Eater's 8-bit computer, also known as the SAP-1 (see here:
https://eater.net/8bit).

It might eventually develop into something more general purpose with some
convenience features targeted at embedded programming.  For example, W65C02S
support is currently in the works.

## Installation and Usage

It's written in python 3 and has no package dependencies.  The only real
version requirement comes from the fact that I use the walrus operator (yeah, I
know I know).  From that, you need at least python 3.8.

To get started, clone the repo, make a virtualenv, and install the package
locally:
```bash
git clone https://github.com/davesque/wes.git

cd wes
python3 -mvenv venv
source venv/bin/activate

pip install .
```

Then, try compiling one of the example files:
```bash
# pipe a file into wes
wes < examples/count.asm
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

# or, specify a file path as an arg
wes examples/count.asm
# ...
```

## Features

The best way to highlight the features is probably just to take a look at an
example program:
```asm
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
```

For those of you who've followed Ben's 8-bit computer build tutorial, the above
program might look sort of familiar.  The general idea is that any line is
either an operation or a literal value.  Also, any line (blank or otherwise)
can be labeled.  Comments are also supported and begin with the ";" character.
Let's go into more detail below.

### Section and data labels

When the compiler sees a label (like "count_up" in the program above), it
determines where its position would be in the generated program code and then
outputs that position whenever the label is encountered as an argument to an
operation.  Labels can appear on their own line (as with the "count_up" label)
or on the same line as an operation mnemonic or data value (as with the "end"
and "incr" labels).  In either case, the label is naming a position in the
generated code.

### Integer formats and code/data interchangeability

In the example program above, the "init" and "incr" labels act sort of like
variables in higher level programming languages.  The reason this works is that
the compiler just outputs whatever values or code it encounters at whatever
position it encounters them.  So, at the position of the "init" label, a
literal value of 42 (in binary) is output by the compiler.

The compiler actually supports 4 different number formats.  We could have
defined the "init" value in all of the following ways:
```asm
init: 0b101010  ; binary
init: 0o52      ; octal
init: 42        ; decimal
init: 0x2a      ; hexadecimal
```

In fact, we could have defined the whole program like this:
```asm
0b00011010       ; lda init

count_up:
  0b11100000     ; out
  0b00101011     ; add incr
  0b01110101     ; jc count_down
  0b01100001     ; jmp count_up

count_down:
  0b11100000     ; out
  0b00111011     ; sub incr
  0b10001001     ; jz end
  0b01100101     ; jmp count_down

end:
  0b11110000

init: 0b00101010
incr: 0b00000001
```

This version of the count program will compile just fine and output identical
program code as the nicer version further up.  The section and data labels in
this case don't actually do anything.  They're just there to make it obvious
how the generated code lines up.

This example should make it clear that the operation mnemonics such as "jmp"
and "add" are really just syntactic sugar for specific bytes that are output at
each position by the compiler.  If you already know what those bytes should be,
you're free to list them out explicitly like we've done here.

Note that there's really no difference between data and code as far as the
compiler is concerned.  That means the onus is on you to make sure you don't
define any values you want to interpret as data before your code. Otherwise,
the computer might try and interpret them as instructions.  In our example
count program, there's a reason that the "variables" are declared at the end.

Here's another version of the count program just for kicks that foregoes using
labels:
```asm
lda 10
out
add 11
jc 5
jmp 1
out
sub 11
jz 9
jmp 5
hlt
42
1
```

This version of the program again compiles to the same output code.

### Offsets

Another interesting feature provided by wes is called *offsets*.  Offsets are
mostly useful for generating ROM images.  In our count program from above, the
two variable labels "init" and "incr" end up pointing to locations in memory
that depend on the length of program code that came before.  However, it is
sometimes convenient to locate labels at specific locations in memory.  Here's
another version of the count program that positions the two values "init" and
"incr" at the last two locations in memory:
```asm
lda init

count_up:
  out
  add incr
  jc count_down
  jmp count_up

count_down:
  out
  sub incr
  jz end
  jmp count_down

end: hlt

-2:
init: 42
incr: 1
```

Since `hlt` is the last instruction to appear before the offset `-2:`, its
encoding is used as a padding value to fill the region of memory between `hlt`
and the literal value `42`.  If we had wanted another padding value, say zeros
for example, we could have written the program as follows:
```asm
; ...

end: hlt

0
-2:
init: 42
incr: 1
```

Note that `0` is now the most recent "instruction" to appear before the offset
`-2:`.  So all memory locations between `hlt` and `42` become zeros.

There are two other ways of specifying offsets.  Assuming we were fine with
`hlt` being used for padding, we could have written the above program in the
following two identical ways.  First, using an absolute offset:
```asm
; ...

end: hlt

14:
init: 42
incr: 1
```

Second, using a forward relative offset:
```asm
; ...

end: hlt

+4:
init: 42
incr: 1
```

Note that `16` (the address space size for the SAP-1) minus `2` is `14`.  So
the absolute offset `14` is equivalent to the backward relative offset `-2`.
Likewise, `10` (the address location of the line immediately after the `hlt`
instruction) plus `4` is `14`.  So the absolute offset `14` is equivalent to
the forward offset `+4` when located on the line after `hlt`.

This feature becomes particularly useful when generating ROMs for the W65C02S.
The W65C02S microprocessor expects a reset vector of two bytes at offset
`0xfffc` in memory.  We may also wish to locate the beginning of our program at
some address other than zero.  We can meet both of those requirements using
offsets:
```asm
0x8000: start:
lda 0
; ...

0
0xfffc: word start
```
The above program snippet locates the beginning of instructions at address
`0x8000`, labeled as `start`.  We can then write arbitrary program code after
this label.  We then specify the offset `0xfffc` (the reset vector address) as
containing the two little-endian bytes of the address labeled by `start`. Since
the offset `0xfffc` was preceded by a literal zero, all bytes after our program
code and before offset `0xfffc` will be zero.  The W65C02S will inspect the
data at `0xfffc` to determine the start address for program execution and find
the little-endian value `0x8000`.  Therefore, execution will begin at address
`0x8000`.

## Examples and contribution

A couple example programs are included in the "examples" directory to get you
started.  Feel free to submit others in a PR if you think you've written
something cool that fits in 16 bytes :).  Bug fixes and modest enhancements are
also welcome.  Hopefully, I'll have time to respond to them.

Cheers, y'all!
