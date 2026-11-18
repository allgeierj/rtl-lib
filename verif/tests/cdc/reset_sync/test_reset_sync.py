"""
cocotb tests for the reset_sync module.

Verifies that rst_o powers up asserted, asserts as soon as async_rst_i rises with no clock
edge needed, and deasserts exactly Stages clk edges after async_rst_i falls. Also checks
that a reset pulse shorter than a clock period is still caught and stretched to Stages
edges, and that reasserting during the release restarts the count.

The model treats the synchroniser as a count of clk edges still needed before release:
async_rst_i high holds it at Stages, and each edge with async_rst_i low counts it down.
Simulation has no metastability, so the +/- 1 cycle uncertainty on release and the
ASYNC_REG placement are not checked here.
"""

import random

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import params, start_clock

P = params()
STAGES = P.get("Stages", 2)
NUM_VERIFY_CYCLES = 500
RESET_PROBABILITY = 0.1
RAND_SEED = 0xDEAD_BEEF


class ResetSyncModel:
    """Reference model: rst_o stays high until STAGES edges pass with async_rst_i low"""

    def __init__(self):
        self.edges_left = STAGES
        self.async_rst = 0

    def set_async_rst(self, value):
        self.async_rst = value
        if value:
            self.edges_left = STAGES

    def clock(self):
        if self.async_rst:
            self.edges_left = STAGES
        elif self.edges_left:
            self.edges_left -= 1

    @property
    def rst(self):
        return int(self.edges_left > 0)


def check(dut, model, ctx):
    result = int(dut.rst_o.value)
    assert result == model.rst, f"(S={STAGES}) {ctx}: got {result}, expected {model.rst}"


async def release(dut):
    """Pulse async_rst_i, then clock until rst_o is low, so DUT matches a released model"""
    dut.async_rst_i.value = 1
    await RisingEdge(dut.clk)
    dut.async_rst_i.value = 0
    for _ in range(STAGES):
        await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    model = ResetSyncModel()
    model.edges_left = 0
    check(dut, model, "after release")
    return model


async def step(dut, model, async_rst, ctx):
    """Clock one edge and check, then change async_rst_i mid-cycle and check before the next edge"""
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    model.clock()
    check(dut, model, f"{ctx} after edge")

    dut.async_rst_i.value = async_rst
    await Timer(1, unit="ns")
    model.set_async_rst(async_rst)
    check(dut, model, f"{ctx} mid-cycle")


@cocotb.test()
async def test_power_up(dut):
    """rst_o powers up high and releases STAGES edges after the clock starts (must run first)"""
    dut.async_rst_i.value = 0
    await Timer(1, unit="ns")
    model = ResetSyncModel()
    check(dut, model, "before first edge")

    start_clock(dut.clk)
    for cycle in range(STAGES + 2):
        await step(dut, model, 0, f"cycle {cycle}")


@cocotb.test()
async def test_async_assert(dut):
    """rst_o rises as soon as async_rst_i does, mid-cycle, without waiting for an edge"""
    start_clock(dut.clk)
    model = await release(dut)

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.async_rst_i.value = 1
    await Timer(1, unit="ns")
    model.set_async_rst(1)
    check(dut, model, "1 ns after async_rst_i rises")


@cocotb.test()
async def test_release_latency(dut):
    """rst_o falls on exactly the STAGES-th edge after async_rst_i falls"""
    start_clock(dut.clk)
    model = await release(dut)

    await step(dut, model, 1, "assert")
    await step(dut, model, 1, "hold")
    for cycle in range(STAGES + 2):
        await step(dut, model, 0, f"release cycle {cycle}")


@cocotb.test()
async def test_short_pulse(dut):
    """A pulse between two edges, never seen by an edge, still holds rst_o for STAGES edges"""
    start_clock(dut.clk)
    model = await release(dut)

    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    dut.async_rst_i.value = 1
    await Timer(1, unit="ns")
    model.set_async_rst(1)
    check(dut, model, "during pulse")
    dut.async_rst_i.value = 0
    await Timer(1, unit="ns")
    model.set_async_rst(0)
    check(dut, model, "after pulse, before edge")

    for cycle in range(STAGES + 2):
        await step(dut, model, 0, f"after pulse {cycle}")


@cocotb.test()
async def test_reassert_during_release(dut):
    """Reasserting part-way through the release restarts the full STAGES-edge count"""
    start_clock(dut.clk)
    model = await release(dut)

    await step(dut, model, 1, "first assert")
    for cycle in range(STAGES - 1):
        await step(dut, model, 0, f"first release {cycle}")
    await step(dut, model, 1, "reassert")
    for cycle in range(STAGES + 2):
        await step(dut, model, 0, f"second release {cycle}")


@cocotb.test()
async def test_random(dut):
    """Random async_rst_i changes mid-cycle; rst_o must follow the model after every edge"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = await release(dut)

    async_rst = 0
    for cycle in range(NUM_VERIFY_CYCLES):
        if random.random() < RESET_PROBABILITY:
            async_rst ^= 1
        await step(dut, model, async_rst, f"cycle {cycle}")
