"""
cocotb tests for the delay_valid module.

The shift/stall behaviour itself is covered by the delay tests; these check that
valid and data stay aligned, share clk_en, and that rst clears valid but not data.
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


class DelayValidModel:
    """Reference model: valid and data lines sharing clk_en, with rst clearing only valid.

    Unconnected ports take their RTL defaults (clk_en = 1, rst = 0).
    """

    def __init__(self):
        self.valid_line = deque([0] * DEPTH, maxlen=DEPTH)
        self.data_line = deque([0] * DEPTH, maxlen=DEPTH)

    def clock(self, valid, data, clk_en, rst):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        rst = rst if CONNECT_RST else 0
        if rst:
            self.valid_line.extend([0] * DEPTH)
        elif clk_en:
            self.valid_line.appendleft(valid)
        if clk_en:
            self.data_line.appendleft(data)

    @property
    def output(self):
        return self.valid_line[-1], self.data_line[-1]


def read_outputs(dut):
    return int(dut.cX_valid_o.value), int(dut.cX_data_o.value)


@cocotb.test(skip=DEPTH == 0)
async def test_reset_value(dut):
    """Both lines are initialized to zero, so the first DEPTH outputs are 0 (must run first)"""
    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_valid_i.value = 1
    dut.c0_data_i.value = mask(WIDTH)
    await Timer(1, unit="ns")
    assert read_outputs(dut) == (0, 0), "outputs not 0 before first edge"

    start_clock(dut.clk)
    for cycle in range(DEPTH - 1):
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")
        valid, data = read_outputs(dut)
        assert (valid, data) == (0, 0), f"cycle {cycle}: got valid={valid} data=0x{data:x}, expected 0"


@cocotb.test(skip=DEPTH == 0 or not CONNECT_RST)
async def test_reset_clears_valid_only(dut):
    """rst zeroes the valid line but leaves the data line shifting"""
    start_clock(dut.clk)

    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_valid_i.value = 1
    dut.c0_data_i.value = mask(WIDTH)
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)

    dut.rst.value = 1
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    valid, data = read_outputs(dut)
    assert valid == 0, f"after reset edge: valid={valid}, expected 0"
    assert data == mask(WIDTH), f"after reset edge: data=0x{data:x}, expected 0x{mask(WIDTH):x} (data must not reset)"


@cocotb.test(skip=DEPTH == 0)
async def test_random_controls(dut):
    """Random valid, data, clk_en and rst checked against the reference model"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)

    # Flush both lines so DUT and a fresh model agree
    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_valid_i.value = 0
    dut.c0_data_i.value = 0
    for _ in range(DEPTH):
        await RisingEdge(dut.clk)

    model = DelayValidModel()
    for cycle in range(NUM_VERIFY_CYCLES):
        valid = random.randint(0, 1)
        data = random.randint(0, mask(WIDTH))
        clk_en = int(random.random() >= STALL_PROBABILITY)
        rst = int(random.random() < RESET_PROBABILITY)
        dut.c0_valid_i.value = valid
        dut.c0_data_i.value = data
        dut.clk_en.value = clk_en
        dut.rst.value = rst
        await RisingEdge(dut.clk)
        await Timer(1, unit="ns")

        model.clock(valid, data, clk_en, rst)
        exp_valid, exp_data = model.output
        got_valid, got_data = read_outputs(dut)
        assert (got_valid, got_data) == (exp_valid, exp_data), (
            f"(W={WIDTH}, D={DEPTH}, rst={'on' if CONNECT_RST else 'off'}, "
            f"clk_en={'on' if CONNECT_CLK_EN else 'off'}) cycle {cycle} "
            f"[clk_en={clk_en} rst={rst}]: got valid={got_valid} data=0x{got_data:x}, "
            f"expected valid={exp_valid} data=0x{exp_data:x}"
        )


@cocotb.test(skip=DEPTH != 0)
async def test_passthrough(dut):
    """Depth == 0 passes valid and data through combinationally, unaffected by clk_en and rst"""
    random.seed(RAND_SEED)
    for _ in range(100):
        valid = random.randint(0, 1)
        data = random.randint(0, mask(WIDTH))
        dut.c0_valid_i.value = valid
        dut.c0_data_i.value = data
        dut.clk_en.value = random.randint(0, 1)
        dut.rst.value = random.randint(0, 1)
        await Timer(1, unit="ns")
        got = read_outputs(dut)
        assert got == (valid, data), f"got {got}, expected {(valid, data)}"
