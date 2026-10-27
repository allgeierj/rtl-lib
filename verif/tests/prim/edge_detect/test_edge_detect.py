"""
cocotb tests for the edge_detect module, written against its header and ports only:

    Per-bit rising/falling/either edge pulses on c0_detect_i, valid when c0_valid_o is high.
    Outputs are combinational from c0_detect_i; c0_detect_i must be synchronous to clk.

Interpretation used by the reference model:
  - A sample of c0_detect_i is taken at every clock edge with clk_en high and rst low.
  - The detector is armed by its first sample after power-up or rst; rst disarms it
    even when clk_en is low. There is no previous value until then, so no edge may be reported.
  - c0_valid_o = clk_en & ~rst & armed; edge outputs are only checked while it is high.
  - While valid, edges compare the live c0_detect_i against the last sample.
  - Unconnected ports take their RTL defaults (clk_en = 1, rst = 0).
"""

import random

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
WIDTH = P.get("Width", 8)
CONNECT_RST = P.get("ConnectRst", 1)
CONNECT_CLK_EN = P.get("ConnectClkEn", 1)
NUM_VERIFY_CYCLES = 500
RESET_PROBABILITY = 0.05
STALL_PROBABILITY = 0.25
RAND_SEED = 0xDEAD_BEEF


class EdgeDetectModel:
    """Reference model: last-sample and armed registers plus combinational edge outputs."""

    def __init__(self, prev, armed=True):
        self.prev = prev
        self.armed = armed

    @staticmethod
    def controls(clk_en, rst):
        return (clk_en if CONNECT_CLK_EN else 1), (rst if CONNECT_RST else 0)

    def clock(self, detect, clk_en, rst):
        clk_en, rst = self.controls(clk_en, rst)
        if rst:
            self.armed = False
        elif clk_en:
            self.prev = detect
            self.armed = True

    def outputs(self, detect, clk_en, rst):
        """Expected (valid, rising, falling, either) for the current inputs."""
        clk_en, rst = self.controls(clk_en, rst)
        valid = int(clk_en and not rst and self.armed)
        rising = ~self.prev & detect & mask(WIDTH)
        falling = self.prev & ~detect & mask(WIDTH)
        return valid, rising, falling, rising | falling


def read_outputs(dut):
    return (
        int(dut.c0_valid_o.value),
        int(dut.c0_rising_o.value),
        int(dut.c0_falling_o.value),
        int(dut.c0_either_o.value),
    )


def check(dut, model, detect, clk_en, rst, ctx):
    """Compare live outputs to the model; edge outputs only matter while valid"""
    exp = model.outputs(detect, clk_en, rst)
    got = read_outputs(dut)
    tag = (
        f"(W={WIDTH}, rst={'on' if CONNECT_RST else 'off'}, "
        f"clk_en={'on' if CONNECT_CLK_EN else 'off'}) {ctx} "
        f"[detect=0x{detect:x} clk_en={clk_en} rst={rst}]"
    )
    assert got[0] == exp[0], f"{tag}: valid={got[0]}, expected {exp[0]}"
    if exp[0]:
        names = ("rising", "falling", "either")
        for name, g, e in zip(names, got[1:], exp[1:]):
            assert g == e, f"{tag}: {name}=0x{g:x}, expected 0x{e:x} (prev sample 0x{model.prev:x})"


async def step(dut, model, detect, clk_en, rst, ctx):
    """Drive inputs mid-cycle, check the combinational outputs, then clock"""
    dut.c0_detect_i.value = detect
    dut.clk_en.value = clk_en
    dut.rst.value = rst
    await Timer(1, unit="ns")
    check(dut, model, detect, clk_en, rst, ctx)
    await RisingEdge(dut.clk)
    model.clock(detect, clk_en, rst)
    await Timer(1, unit="ns")


async def prime(dut, detect=0):
    """Take one enabled sample so the DUT is armed and agrees with a fresh model on the previous value"""
    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_detect_i.value = detect
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")
    return EdgeDetectModel(detect)


@cocotb.test()
async def test_power_up(dut):
    """Not armed until the first sample, so a high input is not an edge (must run first)"""
    dut.rst.value = 0
    dut.clk_en.value = 1
    dut.c0_detect_i.value = mask(WIDTH)
    await Timer(1, unit="ns")

    valid, rising, falling, either = read_outputs(dut)
    if valid:
        assert rising == 0, (
            f"before first clock edge: valid=1 with rising=0x{rising:x} for a level "
            f"never seen low; the first edge would latch a false rising pulse"
        )
        assert falling == 0 and either == 0, f"before first clock edge: falling=0x{falling:x} either=0x{either:x}"


@cocotb.test()
async def test_single_edges(dut):
    """Each 0->1 and 1->0 transition pulses rising/falling for exactly one cycle, per bit"""
    start_clock(dut.clk)
    model = await prime(dut, 0)

    patterns = [0, mask(WIDTH), mask(WIDTH), 0, 0]
    # Walk a single bit through every position, then an alternating pattern
    for bit in range(WIDTH):
        patterns += [1 << bit, 1 << bit, 0]
    alt = int("10" * WIDTH, 2) & mask(WIDTH)
    patterns += [alt, alt ^ mask(WIDTH), alt, alt]

    for cycle, detect in enumerate(patterns):
        await step(dut, model, detect, 1, 0, f"pattern {cycle}")


@cocotb.test()
async def test_combinational(dut):
    """Outputs follow c0_detect_i between clock edges, with no edge in between"""
    start_clock(dut.clk)
    model = await prime(dut, 0)

    # Two changes within one cycle (edges at 4 ns intervals; offsets stay inside it)
    dut.c0_detect_i.value = mask(WIDTH)
    await Timer(1, unit="ns")
    check(dut, model, mask(WIDTH), 1, 0, "mid-cycle high")
    dut.c0_detect_i.value = 0
    await Timer(1, unit="ns")
    check(dut, model, 0, 1, 0, "mid-cycle back low")


@cocotb.test(skip=not CONNECT_CLK_EN)
async def test_clk_en_stall(dut):
    """clk_en low drops valid and takes no sample; edges are measured between enabled samples"""
    start_clock(dut.clk)
    model = await prime(dut, 0)

    # A pulse entirely inside a stall is never seen
    await step(dut, model, mask(WIDTH), 0, 0, "stall high")
    await step(dut, model, 0, 0, 0, "stall low")
    await step(dut, model, 0, 1, 0, "resume after hidden pulse")

    # A level change during a stall is reported once, on the first enabled cycle
    await step(dut, model, mask(WIDTH), 0, 0, "stall rise")
    await step(dut, model, mask(WIDTH), 0, 0, "stall hold")
    await step(dut, model, mask(WIDTH), 1, 0, "resume reports rise")
    await step(dut, model, mask(WIDTH), 1, 0, "rise not repeated")


@cocotb.test(skip=not CONNECT_RST)
async def test_reset(dut):
    """rst drops valid and disarms; the first sample after reset only re-arms"""
    start_clock(dut.clk)
    model = await prime(dut, 0)

    await step(dut, model, mask(WIDTH), 1, 0, "rise before reset")
    for cycle in range(3):
        await step(dut, model, mask(WIDTH), 1, 1, f"reset {cycle}")
    await step(dut, model, mask(WIDTH), 1, 0, "arming sample, held high")
    await step(dut, model, mask(WIDTH), 1, 0, "held high after re-arm")

    # The arming sample is the new reference, whatever was seen before or during reset
    await step(dut, model, 0, 1, 1, "reset, fall")
    await step(dut, model, mask(WIDTH), 1, 1, "reset, rise")
    await step(dut, model, 0, 1, 0, "arming sample, low")
    await step(dut, model, mask(WIDTH), 1, 0, "rise after re-arm")


@cocotb.test(skip=not (CONNECT_RST and CONNECT_CLK_EN))
async def test_reset_while_stalled(dut):
    """rst disarms even when clk_en is low"""
    start_clock(dut.clk)
    model = await prime(dut, 0)

    await step(dut, model, mask(WIDTH), 0, 1, "stalled reset, input high")
    await step(dut, model, mask(WIDTH), 0, 0, "still stalled")
    await step(dut, model, mask(WIDTH), 1, 0, "arming sample, no rise")
    await step(dut, model, 0, 1, 0, "fall after re-arm")


@cocotb.test()
async def test_random_controls(dut):
    """Random detect, clk_en and rst checked against the reference model.

    When a port is unconnected the random values on its pin must have no effect.
    """
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = await prime(dut, 0)

    detect = 0
    for cycle in range(NUM_VERIFY_CYCLES):
        # Flip a random subset of bits so each bit sees both edges often
        detect ^= random.randint(0, mask(WIDTH))
        clk_en = int(random.random() >= STALL_PROBABILITY)
        rst = int(random.random() < RESET_PROBABILITY)
        await step(dut, model, detect, clk_en, rst, f"cycle {cycle}")
