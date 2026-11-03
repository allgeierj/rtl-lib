"""
cocotb tests for the sync_ff module.

Verifies that c0_data_i reaches cL_data_o exactly Stages capture_clk edges later, that
the synchroniser powers up as zero, that every bit is passed independently, and that
single-cycle pulses are neither filtered nor stretched.

Simulation has no metastability, so the model is an ideal Stages-deep shift register. The
+/- 1 cycle uncertainty of a real crossing and the ASYNC_REG placement are not checked here.
"""

import random
from collections import deque

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
WIDTH = P.get("Width", 1)
STAGES = P.get("Stages", 2)
NUM_VERIFY_CYCLES = 500
RAND_SEED = 0xDEAD_BEEF


class SyncFfModel:
    """Reference model: a STAGES-entry shift register, initialised to zero"""

    def __init__(self):
        self.line = deque([0] * STAGES, maxlen=STAGES)

    def clock(self, data):
        self.line.appendleft(data)

    @property
    def output(self):
        return self.line[-1]


async def flush(dut):
    """Shift zeros through every stage so DUT and a fresh SyncFfModel agree"""
    dut.c0_data_i.value = 0
    for _ in range(STAGES):
        await RisingEdge(dut.clk)


async def step(dut, model, data, ctx):
    """Drive one cycle, clock the model, and check the output after the edge"""
    dut.c0_data_i.value = data
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    model.clock(data)
    result = int(dut.cL_data_o.value)
    assert result == model.output, (
        f"(W={WIDTH}, S={STAGES}) {ctx}: got 0x{result:x}, expected 0x{model.output:x}"
    )
    return result


@cocotb.test()
async def test_power_up(dut):
    """Stages power up as zero, so the first STAGES-1 outputs are 0 (must run first)"""
    dut.c0_data_i.value = mask(WIDTH)
    await Timer(1, unit="ns")
    result = int(dut.cL_data_o.value)
    assert result == 0, f"(W={WIDTH}, S={STAGES}) before first edge: got 0x{result:x}, expected 0"

    start_clock(dut.clk)
    for cycle in range(STAGES):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        expected = mask(WIDTH) if cycle == STAGES - 1 else 0
        result = int(dut.cL_data_o.value)
        assert result == expected, (
            f"(W={WIDTH}, S={STAGES}) cycle {cycle}: got 0x{result:x}, expected 0x{expected:x}"
        )


@cocotb.test()
async def test_pulse(dut):
    """A one-cycle pulse appears exactly STAGES edges later and lasts one cycle"""
    start_clock(dut.clk)
    await flush(dut)
    model = SyncFfModel()

    await step(dut, model, mask(WIDTH), "pulse")
    for cycle in range(STAGES + 2):
        await step(dut, model, 0, f"after pulse {cycle}")


@cocotb.test()
async def test_walking_one(dut):
    """Each bit is synchronised independently, with no crosstalk between bits"""
    start_clock(dut.clk)
    await flush(dut)
    model = SyncFfModel()

    for bit in range(WIDTH):
        await step(dut, model, 1 << bit, f"bit {bit}")
    for cycle in range(STAGES):
        await step(dut, model, 0, f"drain {cycle}")


@cocotb.test()
async def test_random_streaming(dut):
    """Random data every cycle, output must equal the input from STAGES edges earlier"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    await flush(dut)
    model = SyncFfModel()

    for cycle in range(NUM_VERIFY_CYCLES):
        await step(dut, model, random.randint(0, mask(WIDTH)), f"cycle {cycle}")
