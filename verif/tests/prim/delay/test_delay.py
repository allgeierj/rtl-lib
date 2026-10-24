"""
cocotb tests for the delay module.

Verifies input data is delayed by Depth cycles (combinational when Depth == 0),
and that rst clears the delay line only when ResetEn is set.
"""

import random
from collections import deque

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
WIDTH = P.get("Width", 8)
DEPTH = P.get("Depth", 1)
RESET_EN = P.get("ResetEn", 0)
NUM_VERIFY_CYCLES = 500
RESET_PROBABILITY = 0.05
RAND_SEED = 0xDEAD_BEEF


class DelayModel:
    """Reference model: a DEPTH-entry shift register, cleared by rst when RESET_EN."""

    def __init__(self):
        self.line = deque([0] * DEPTH, maxlen=DEPTH)

    def clock(self, data, rst):
        if RESET_EN and rst:
            self.line.extend([0] * DEPTH)
        else:
            self.line.appendleft(data)

    @property
    def output(self):
        return self.line[-1]


@cocotb.test(skip=DEPTH == 0)
async def test_reset_value(dut):
    """Delay line is initialized to zero, so the first DEPTH outputs are 0 (must run first)"""
    dut.rst.value = 0
    dut.c0_data_i.value = mask(WIDTH)
    await Timer(1, unit="ns")
    assert int(dut.cX_data_o.value) == 0, "output not 0 before first edge"

    start_clock(dut.clk)
    for cycle in range(DEPTH - 1):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        result = int(dut.cX_data_o.value)
        assert result == 0, f"cycle {cycle}: got 0x{result:x}, expected 0"


@cocotb.test()
async def test_random_streaming(dut):
    """Continuous random data, output must equal input from DEPTH cycles ago"""
    dut.rst.value = 0
    start_clock(dut.clk)
    random.seed(RAND_SEED)

    num_cycles = DEPTH + NUM_VERIFY_CYCLES
    inputs = [random.randint(0, mask(WIDTH)) for _ in range(num_cycles)]

    for cycle in range(num_cycles):
        dut.c0_data_i.value = inputs[cycle]
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        # After edge `cycle`, the output holds the value sampled DEPTH-1 edges earlier
        src = cycle - DEPTH + 1
        if DEPTH > 0 and src >= 0:
            result = int(dut.cX_data_o.value)
            assert result == inputs[src], (
                f"(W={WIDTH}, D={DEPTH}) cycle {cycle}: "
                f"got 0x{result:x}, expected 0x{inputs[src]:x}"
            )


@cocotb.test(skip=DEPTH == 0 or not RESET_EN)
async def test_reset_clears(dut):
    """A one-cycle rst zeroes the whole line, discarding the data sampled with it"""
    start_clock(dut.clk)

    # Fill the line with nonzero data
    dut.rst.value = 0
    dut.c0_data_i.value = mask(WIDTH)
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)

    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    result = int(dut.cX_data_o.value)
    assert result == 0, f"after reset edge: got 0x{result:x}, expected 0"

    # Zeros drain out over the next DEPTH-1 edges, then post-reset data arrives
    for cycle in range(DEPTH):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        expected = mask(WIDTH) if cycle == DEPTH - 1 else 0
        result = int(dut.cX_data_o.value)
        assert result == expected, (
            f"cycle {cycle} after reset: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test(skip=DEPTH == 0)
async def test_random_reset(dut):
    """Random data with randomly asserted rst, checked against the reference model"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)

    # Flush the line so DUT and model start from the same (all-zero) state
    dut.rst.value = 0
    dut.c0_data_i.value = 0
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)

    model = DelayModel()
    for cycle in range(NUM_VERIFY_CYCLES):
        data = random.randint(0, mask(WIDTH))
        rst = int(random.random() < RESET_PROBABILITY)
        dut.c0_data_i.value = data
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        model.clock(data, rst)
        result = int(dut.cX_data_o.value)
        assert result == model.output, (
            f"(W={WIDTH}, D={DEPTH}, R={RESET_EN}) cycle {cycle} rst={rst}: "
            f"got 0x{result:x}, expected 0x{model.output:x}"
        )


@cocotb.test(skip=DEPTH != 0)
async def test_passthrough(dut):
    """Depth == 0 is a combinational passthrough, unaffected by rst"""
    random.seed(RAND_SEED)
    for _ in range(100):
        value = random.randint(0, mask(WIDTH))
        dut.c0_data_i.value = value
        dut.rst.value = random.randint(0, 1)
        await Timer(1, unit="ns")
        result = int(dut.cX_data_o.value)
        assert result == value, f"got 0x{result:x}, expected 0x{value:x}"
