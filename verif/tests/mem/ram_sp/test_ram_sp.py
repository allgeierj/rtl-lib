"""
cocotb tests for the ram_sp module.

Verifies the 1-cycle synchronous read, writes to every address, read-first behaviour
(reading the address being written returns the old word), that clk_en low blocks writes
and holds c1_rd_data_o, the clk_en default (1) when unconnected, and InitFile loading.

Words are undefined until written (or loaded from InitFile) and c1_rd_data_o is undefined
until the first enabled read, so the model tracks those values as unknown and skips checking
them. Verilator is 2-state, so the X itself is not observable here.
"""

import random
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
ADDR_WIDTH = P.get("AddrWidth", 12)
WIDTH = P.get("Width", 9)
CONNECT_CLK_EN = P.get("ConnectClkEn", 1)
USE_INIT_FILE = P.get("UseInitFile", 0)
DEPTH = 1 << ADDR_WIDTH
INIT_FILE = Path(__file__).parent / "ram_sp_init.hex"
NUM_VERIFY_CYCLES = 1000
STALL_PROBABILITY = 0.25
WRITE_PROBABILITY = 0.5
RAND_SEED = 0xDEAD_BEEF


class RamModel:
    """Reference model: DEPTH words, 1-cycle read latency, read-first.

    Unknown words and an unknown output are None. An unconnected clk_en takes its RTL
    default of 1, so the value driven on its pin is ignored.
    """

    def __init__(self, contents=None):
        self.mem = dict(contents or {})
        self.rd_data = None

    def clock(self, clk_en, wr_en, addr, data):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        if not clk_en:
            return
        self.rd_data = self.mem.get(addr)
        if wr_en:
            self.mem[addr] = data


def load_init_file():
    """Words of INIT_FILE in address order, as $readmemh reads them"""
    words = []
    for line in INIT_FILE.read_text().splitlines():
        words += [int(tok, 16) for tok in line.split("//")[0].split()]
    return words


async def step(dut, model, clk_en, wr_en, addr, data, ctx):
    """Drive one cycle, clock the model, and check c1_rd_data_o after the edge.

    Returns the output, or None when the model says it is unknown.
    """
    dut.clk_en.value = clk_en
    dut.c0_wr_enable_i.value = wr_en
    dut.c0_address_i.value = addr
    dut.c0_wr_data_i.value = data
    await RisingEdge(dut.clk)
    await Timer(1, unit="ns")

    model.clock(clk_en, wr_en, addr, data)
    if model.rd_data is None:
        return None
    result = int(dut.c1_rd_data_o.value)
    assert result == model.rd_data, (
        f"(AW={ADDR_WIDTH}, W={WIDTH}, clk_en={'on' if CONNECT_CLK_EN else 'off'}) {ctx} "
        f"[clk_en={clk_en} we={wr_en} addr=0x{addr:x} wdata=0x{data:x}]: "
        f"got 0x{result:x}, expected 0x{model.rd_data:x}"
    )
    return result


@cocotb.test(skip=not USE_INIT_FILE)
async def test_init_file(dut):
    """Every word reads back as loaded from InitFile (must run first, before any write)"""
    words = load_init_file()
    assert len(words) == DEPTH and max(words) <= mask(WIDTH), (
        f"{INIT_FILE.name} holds {len(words)} words up to 0x{max(words):x}, "
        f"which does not fit AW={ADDR_WIDTH}, W={WIDTH}"
    )
    start_clock(dut.clk)
    model = RamModel(enumerate(words))

    for addr in range(DEPTH):
        await step(dut, model, 1, 0, addr, 0, f"read {addr}")
    # The last address is read out on this edge
    await step(dut, model, 1, 0, 0, 0, "final read")


@cocotb.test()
async def test_write_read_all(dut):
    """A random word written to every address reads back, in shuffled order"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = RamModel()

    for addr in range(DEPTH):
        await step(dut, model, 1, 1, addr, random.randint(0, mask(WIDTH)), f"write {addr}")

    order = list(range(DEPTH))
    random.shuffle(order)
    for addr in order:
        await step(dut, model, 1, 0, addr, random.randint(0, mask(WIDTH)), f"read {addr}")
    await step(dut, model, 1, 0, 0, 0, "final read")


@cocotb.test()
async def test_read_first(dut):
    """Reading the address being written returns the old word; the next read returns the new one"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = RamModel()

    for trial in range(8):
        addr = random.randrange(DEPTH)
        old = random.randint(0, mask(WIDTH))
        new = old ^ mask(WIDTH)
        await step(dut, model, 1, 1, addr, old, f"trial {trial} write old")
        result = await step(dut, model, 1, 1, addr, new, f"trial {trial} write new")
        assert result == old, f"trial {trial}: write cycle returned 0x{result:x}, expected old 0x{old:x}"
        result = await step(dut, model, 1, 0, addr, 0, f"trial {trial} read back")
        assert result == new, f"trial {trial}: read back 0x{result:x}, expected new 0x{new:x}"


@cocotb.test(skip=not CONNECT_CLK_EN)
async def test_clk_en_stall(dut):
    """With clk_en low, writes are ignored and c1_rd_data_o holds while the address changes"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = RamModel()

    a, b = random.sample(range(DEPTH), 2)
    await step(dut, model, 1, 1, a, random.randint(0, mask(WIDTH)), "write a")
    await step(dut, model, 1, 1, b, random.randint(0, mask(WIDTH)), "write b")
    held = await step(dut, model, 1, 0, a, 0, "read a")

    for cycle in range(4):
        addr = (a, b)[cycle % 2]
        result = await step(dut, model, 0, 1, addr, random.randint(0, mask(WIDTH)), f"stall {cycle}")
        assert result == held, f"stall {cycle}: output changed 0x{held:x} -> 0x{result:x}"

    # Stalled writes never landed, so both words still hold their pre-stall values
    await step(dut, model, 1, 0, a, 0, "resume read a")
    await step(dut, model, 1, 0, b, 0, "resume read b")
    await step(dut, model, 1, 0, 0, 0, "final read")


@cocotb.test()
async def test_random(dut):
    """Random writes, reads and clk_en checked against the reference model.

    Addresses mostly come from a small pool so reads often hit written words. When clk_en is
    unconnected, the random values on its pin must have no effect.
    """
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = RamModel()
    pool = random.sample(range(DEPTH), min(DEPTH, 16))

    for cycle in range(NUM_VERIFY_CYCLES):
        clk_en = int(random.random() >= STALL_PROBABILITY)
        wr_en = int(random.random() < WRITE_PROBABILITY)
        addr = random.choice(pool) if random.random() < 0.9 else random.randrange(DEPTH)
        await step(dut, model, clk_en, wr_en, addr, random.randint(0, mask(WIDTH)), f"cycle {cycle}")
