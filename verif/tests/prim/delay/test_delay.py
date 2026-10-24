"""
cocotb tests for the delay module.

Verifies input data is delayed by Depth cycles (combinational when Depth == 0).
"""

import random

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
WIDTH = P.get("Width", 8)
DEPTH = P.get("Depth", 1)
NUM_VERIFY_CYCLES = 500
RAND_SEED = 0xDEAD_BEEF


@cocotb.test(skip=DEPTH == 0)
async def test_reset_value(dut):
    """Delay line is initialized to zero, so the first DEPTH outputs are 0 (must run first)"""
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


@cocotb.test(skip=DEPTH != 0)
async def test_passthrough(dut):
    """Depth == 0 is a combinational passthrough"""
    random.seed(RAND_SEED)
    for _ in range(100):
        value = random.randint(0, mask(WIDTH))
        dut.c0_data_i.value = value
        await Timer(1, unit="ns")
        result = int(dut.cX_data_o.value)
        assert result == value, f"got 0x{result:x}, expected 0x{value:x}"
