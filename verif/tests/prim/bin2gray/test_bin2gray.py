"""
cocotb tests for the bin2gray module.

Verifies c0_gray_o is the standard reflected binary Gray code of c0_bin_i. The module is
purely combinational with no clock, so every check drives an input and reads the output
after a short settle time.

Widths up to EXHAUSTIVE_MAX_WIDTH cover every input value; wider ones use directed corners
(all carry boundaries, walking ones) plus random values.
"""

import random

import cocotb
from cocotb.triggers import Timer

from tb_lib import mask, params

P = params()
WIDTH = P.get("Width", 8)
EXHAUSTIVE_MAX_WIDTH = 16
NUM_RANDOM_VALUES = 500
RAND_SEED = 0xDEAD_BEEF

# The reflected code for 0..15; narrower widths use the leading 2**Width entries
GRAY_SEQUENCE = [
    0b0000, 0b0001, 0b0011, 0b0010, 0b0110, 0b0111, 0b0101, 0b0100,
    0b1100, 0b1101, 0b1111, 0b1110, 0b1010, 0b1011, 0b1001, 0b1000,
]


def bit(value, index):
    return (value >> index) & 1


def expected_gray(value):
    """Per-bit definition: the MSB is copied, every other bit XORs with its upper neighbour"""
    result = bit(value, WIDTH - 1) << (WIDTH - 1)
    for i in range(WIDTH - 1):
        result |= (bit(value, i) ^ bit(value, i + 1)) << i
    return result


def gray_to_bin(gray):
    """Standard Gray decode: each binary bit is the XOR of all Gray bits at or above it"""
    result = 0
    parity = 0
    for i in reversed(range(WIDTH)):
        parity ^= bit(gray, i)
        result |= parity << i
    return result


def input_values():
    """Every input for small widths; otherwise corners, carry boundaries and random values"""
    if WIDTH <= EXHAUSTIVE_MAX_WIDTH:
        return list(range(1 << WIDTH))

    random.seed(RAND_SEED)
    values = {0, mask(WIDTH)}
    for i in range(WIDTH):
        values |= {1 << i, (1 << i) - 1, mask(WIDTH) ^ (1 << i)}
    values |= {random.randint(0, mask(WIDTH)) for _ in range(NUM_RANDOM_VALUES)}
    return sorted(values)


async def convert(dut, value):
    dut.c0_bin_i.value = value
    await Timer(1, unit="ns")
    return int(dut.c0_gray_o.value)


@cocotb.test()
async def test_reflected_sequence(dut):
    """The first codes match the published reflected binary sequence"""
    for value, expected in enumerate(GRAY_SEQUENCE[: 1 << WIDTH]):
        result = await convert(dut, value)
        assert result == expected, (
            f"(W={WIDTH}) bin 0x{value:x}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_conversion(dut):
    """Output matches the per-bit definition"""
    for value in input_values():
        result = await convert(dut, value)
        expected = expected_gray(value)
        assert result == expected, (
            f"(W={WIDTH}) bin 0x{value:x}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_msb_not_sign_extended(dut):
    """All ones gives only the MSB set, so the shift must fill with zero"""
    result = await convert(dut, mask(WIDTH))
    expected = 1 << (WIDTH - 1)
    assert result == expected, (
        f"(W={WIDTH}) all ones: got 0x{result:x}, expected 0x{expected:x}"
    )


@cocotb.test()
async def test_walking_one(dut):
    """Input bit i affects only output bits i and i-1"""
    for i in range(WIDTH):
        result = await convert(dut, 1 << i)
        expected = (1 << i) | ((1 << i) >> 1)
        assert result == expected, (
            f"(W={WIDTH}) input bit {i}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_adjacent_codes_differ_by_one_bit(dut):
    """Consecutive values differ in exactly one output bit, including the wrap to zero"""
    for value in input_values():
        following = (value + 1) & mask(WIDTH)
        first = await convert(dut, value)
        second = await convert(dut, following)
        changed = first ^ second
        assert changed.bit_count() == 1, (
            f"(W={WIDTH}) bin 0x{value:x} -> 0x{following:x}: "
            f"gray 0x{first:x} -> 0x{second:x} changes {changed.bit_count()} bits"
        )


@cocotb.test()
async def test_round_trip(dut):
    """Decoding the output recovers the input, so the mapping loses no information"""
    for value in input_values():
        result = await convert(dut, value)
        decoded = gray_to_bin(result)
        assert decoded == value, (
            f"(W={WIDTH}) bin 0x{value:x}: gray 0x{result:x} decodes to 0x{decoded:x}"
        )
