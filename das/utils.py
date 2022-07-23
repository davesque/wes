BASES = {
    "0b": 2,
    "0o": 8,
    "0x": 16,
}


def str_to_int(s: str) -> int:
    prefix = s[:2]
    base = BASES.get(prefix, 10)

    return int(s, base=base)


def byte_length(i: int) -> int:
    return max(1, (i.bit_length() + 7) // 8)
