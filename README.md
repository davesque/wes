# dac

This is a bare bones assembly compiler written as a quick hack to generate
instruction code for Ben Eater's 8-bit computer project (see here:
https://eater.net/8bit).  The name, "dac", stand for David's Assembly Compiler.
However, if you're frustrated with its lack of features, you can call it Dumb
Assembly Compiler too, but that'll cost you some karma.

## Installation

It's written in python 3 and has no package dependencies.  It also doesn't
really have any serious version dependencies.  Your system python 3 will
probably run this thing.  Quickest way to install is just to clone this repo
and compile a code file from the repo root dir:

```bash
git clone https://github.com/davesque/dac.git
cd dac

./dac < my_prog.asm
# or
./dac my_prog.asm
```

## Features (or lack thereof?)

Don't expect any nice syntax error printouts.  All you'll get are some basic
error messages telling you that you might have used an op name as a section
label or maybe forgot an argument to a unary op; things like that.  Ben's
computer only has 16 bytes of RAM anyway so we can only write programs that are
at most 16 instructions long.  It shouldn't be that hard to figure out what the
compiler doesn't like if it throws an error.

### Section and data labels

One neat thing is that you can label code sections and also data values:

```asm
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
```

When the compiler sees a label (like "count_up" in the program above), it
determines where its position would be in the generated program code and then
outputs that position whenever the label is encountered as an argument to an
operation.  Labels can appear on their own line (as with the "count_up" label)
or on the same line as an operation mnemonic or data value (as with the "end"
and "incr" labels).  In either case, the label is naming a position in the
generated code.

### Integer formats and code/data interchangeability

Well, I think these are "features" anyway.  In the example program above, the
"init" and "incr" labels act sort of like variables in higher level programming
languages.  The reason this works is that the compiler just outputs whatever
values or code it encounters at whatever position it encounters them.  So, at
the position of the "init" label, a literal value of 42 (in binary) is output
by the compiler.

The compiler actually supports 4 different number formats.  We could have
defined the "init" value in all of the following ways:

```asm
init: 0b101010  # binary
init: 0o52      # octal
init: 42        # decimal
init: 0x2a      # hexadecimal
```

In fact, we could have defined the whole program like this:

```asm
0b00011010       # lda init

count_up:
  0b11100000     # out
  0b00101011     # add incr
  0b01110101     # jc count_down
  0b01100001     # jmp count_up

count_down:
  0b11100000     # out
  0b00111011     # sub incr
  0b10001001     # jz end
  0b01100101     # jmp count_down

end:
  0b11110000

init: 0b00101010
incr: 0b00000001
```

The labels in the version above don't end up doing much.  They're just there
for comparison.  So there's really no difference between values and code as far
as the compiler is concerned.  That means the onus is on you to make sure you
don't define any data values before your code.  Otherwise, the computer might
try and interpret them as instructions.  In our example count program, there's
a reason that the "variables" are declared at the end.

## Examples and contribution

A couple example programs are included in the "examples" directory to get you
started.  Feel free to submit others in a PR if you think you've written
something cool that fits in 16 bytes :).  Bug fixes and modest enhancements are
also welcome.  Hopefully, I'll have time to respond to them.

Cheers, y'all!
