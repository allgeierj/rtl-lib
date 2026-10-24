"""
cocotb tests for the delay module.

Verifies input data is delayed by Depth enabled cycles (combinational when Depth == 0),
that rst clears the delay line and overrides clk_en, and that the clk_en/rst port
defaults (1/0) apply when the testbench leaves them unconnected.
"""

import random
from collections import deque

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
WIDTH = P.get("Width", 8)
DEPTH = P.get("Depth", 1)
CONNECT_RST = P.get("ConnectRst", 1)
CONNECT_CLK_EN = P.get("ConnectClkEn", 1)
NUM_VERIFY_CYCLES = 500
RESET_PROBABILITY = 0.05
STALL_PROBABILITY = 0.25
RAND_SEED = 0xDEAD_BEEF


class DelayModel:
    """Reference model: a DEPTH-entry shift register with clock enable and reset.

    Unconnected ports take their RTL defaults (clk_en = 1, rst = 0), so the values
    driven on the testbench pins are ignored for them.
    """

    def __init__(self):
        self.line = deque([0] * DEPTH, maxlen=DEPTH)

    def clock(self, data, clk_en, rst):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        rst = rst if CONNECT_RST else 0
        if rst:
            self.line.extend([0] * DEPTH)
        elif clk_en:
            self.line.appendleft(data)

    @property
    def output(self):
        return self.line[-1]


async def flush(dut):
    """Shift zeros through the whole line so DUT and a fresh DelayModel agree"""
    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_data_i.value = 0
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)


async def step(dut, model, data, clk_en, rst, ctx):
    """Drive one cycle, clock the model, and check the output after the edge"""
    dut.c0_data_i.value = data
    dut.clk_en.value = clk_en
    dut.rst.value = rst
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    model.clock(data, clk_en, rst)
    result = int(dut.cX_data_o.value)
    assert result == model.output, (
        f"(W={WIDTH}, D={DEPTH}, rst={'on' if CONNECT_RST else 'off'}, "
        f"clk_en={'on' if CONNECT_CLK_EN else 'off'}) {ctx} "
        f"[clk_en={clk_en} rst={rst}]: got 0x{result:x}, expected 0x{model.output:x}"
    )
    return result


@cocotb.test(skip=DEPTH == 0)
async def test_reset_value(dut):
    """Delay line is initialized to zero, so the first DEPTH outputs are 0 (must run first)"""
    dut.rst.value = 0
    dut.clk_en.value = 1
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
    dut.clk_en.value = 1
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


@cocotb.test(skip=DEPTH == 0 or not CONNECT_RST)
async def test_reset_clears(dut):
    """A one-cycle rst zeroes the whole line, discarding the data sampled with it"""
    dut.clk_en.value = 1
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


@cocotb.test(skip=DEPTH == 0 or not CONNECT_CLK_EN)
async def test_clk_en_stall(dut):
    """With clk_en low the line holds its contents and ignores input, then resumes"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    await flush(dut)
    model = DelayModel()

    for cycle in range(DEPTH):
        await step(dut, model, random.randint(0, mask(WIDTH)), 1, 0, f"fill {cycle}")

    held = int(dut.cX_data_o.value)
    for cycle in range(DEPTH + 2):
        result = await step(dut, model, random.randint(0, mask(WIDTH)), 0, 0, f"stall {cycle}")
        assert result == held, f"stall {cycle}: output changed 0x{held:x} -> 0x{result:x}"

    # Resuming must continue from the pre-stall contents; stalled inputs were never captured
    for cycle in range(DEPTH + 1):
        await step(dut, model, random.randint(0, mask(WIDTH)), 1, 0, f"resume {cycle}")


@cocotb.test(skip=DEPTH == 0 or not CONNECT_RST or not CONNECT_CLK_EN)
async def test_reset_while_stalled(dut):
    """rst clears the line even when clk_en is low"""
    start_clock(dut.clk)

    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_data_i.value = mask(WIDTH)
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)

    dut.clk_en.value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    result = int(dut.cX_data_o.value)
    assert result == 0, f"after stalled reset edge: got 0x{result:x}, expected 0"

    # Still stalled: the cleared line must stay cleared
    for cycle in range(DEPTH + 1):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        result = int(dut.cX_data_o.value)
        assert result == 0, f"stall {cycle} after reset: got 0x{result:x}, expected 0"


@cocotb.test(skip=DEPTH == 0)
async def test_random_controls(dut):
    """Random data, clk_en and rst checked against the reference model.

    When a port is unconnected the random values on its pin must have no effect.
    """
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    await flush(dut)
    model = DelayModel()

    for cycle in range(NUM_VERIFY_CYCLES):
        data = random.randint(0, mask(WIDTH))
        clk_en = int(random.random() >= STALL_PROBABILITY)
        rst = int(random.random() < RESET_PROBABILITY)
        await step(dut, model, data, clk_en, rst, f"cycle {cycle}")


@cocotb.test(skip=DEPTH != 0)
async def test_passthrough(dut):
    """Depth == 0 is a combinational passthrough, unaffected by clk_en and rst"""
    random.seed(RAND_SEED)
    for _ in range(100):
        value = random.randint(0, mask(WIDTH))
        dut.c0_data_i.value = value
        dut.clk_en.value = random.randint(0, 1)
        dut.rst.value = random.randint(0, 1)
        await Timer(1, unit="ns")
        result = int(dut.cX_data_o.value)
        assert result == value, f"got 0x{result:x}, expected 0x{value:x}"
