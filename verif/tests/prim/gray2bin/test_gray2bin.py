"""
cocotb tests for the gray2bin module.

Verifies c0_bin_o is the binary value whose standard reflected binary Gray code is
c0_gray_i, i.e. the inverse of bin2gray. The module is purely combinational with no clock,
so every check drives an input and reads the output after a short settle time.

Widths up to EXHAUSTIVE_MAX_WIDTH cover every input value; wider ones use directed corners
(walking ones, walking zeros, all ones) plus random values.
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


def expected_bin(gray):
    """Per-bit definition: each binary bit is the XOR (parity) of all Gray bits at or above it"""
    result = 0
    for i in range(WIDTH):
        parity = 0
        for j in range(i, WIDTH):
            parity ^= bit(gray, j)
        result |= parity << i
    return result


def bin_to_gray(value):
    """Standard Gray encode, used to check the round trip"""
    return (value ^ (value >> 1)) & mask(WIDTH)


def input_values():
    """Every input for small widths; otherwise corners and random values"""
    if WIDTH <= EXHAUSTIVE_MAX_WIDTH:
        return list(range(1 << WIDTH))

    random.seed(RAND_SEED)
    values = {0, mask(WIDTH)}
    for i in range(WIDTH):
        values |= {1 << i, (1 << i) - 1, mask(WIDTH) ^ (1 << i)}
    values |= {random.randint(0, mask(WIDTH)) for _ in range(NUM_RANDOM_VALUES)}
    return sorted(values)


async def convert(dut, gray):
    dut.c0_gray_i.value = gray
    await Timer(1, unit="ns")
    return int(dut.c0_bin_o.value)


@cocotb.test()
async def test_reflected_sequence(dut):
    """The published reflected binary sequence decodes to 0, 1, 2, ..."""
    for expected, gray in enumerate(GRAY_SEQUENCE[: 1 << WIDTH]):
        result = await convert(dut, gray)
        assert result == expected, (
            f"(W={WIDTH}) gray 0x{gray:x}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_conversion(dut):
    """Output matches the per-bit parity definition"""
    for gray in input_values():
        result = await convert(dut, gray)
        expected = expected_bin(gray)
        assert result == expected, (
            f"(W={WIDTH}) gray 0x{gray:x}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_walking_one(dut):
    """Gray bit i alone sets binary bits i and below"""
    for i in range(WIDTH):
        result = await convert(dut, 1 << i)
        expected = mask(i + 1)
        assert result == expected, (
            f"(W={WIDTH}) gray bit {i}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_msb_only(dut):
    """Only the MSB set decodes to all ones, so the top bit reaches every output"""
    result = await convert(dut, 1 << (WIDTH - 1))
    expected = mask(WIDTH)
    assert result == expected, (
        f"(W={WIDTH}) MSB only: got 0x{result:x}, expected 0x{expected:x}"
    )


@cocotb.test()
async def test_round_trip(dut):
    """Decoding the Gray code of every value recovers that value"""
    for value in input_values():
        gray = bin_to_gray(value)
        result = await convert(dut, gray)
        assert result == value, (
            f"(W={WIDTH}) bin 0x{value:x}: gray 0x{gray:x} decodes to 0x{result:x}"
        )


@cocotb.test(skip=WIDTH > EXHAUSTIVE_MAX_WIDTH)
async def test_bijective(dut):
    """Every input decodes to a distinct value"""
    seen = {}
    for gray in input_values():
        result = await convert(dut, gray)
        assert result not in seen, (
            f"(W={WIDTH}) gray 0x{gray:x} and 0x{seen[result]:x} both decode to 0x{result:x}"
        )
        seen[result] = gray
