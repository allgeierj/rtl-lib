"""
cocotb tests for the ram_sp module.

Verifies the synchronous read with Latency = 1 + OutputReg cycles, writes to every address,
read-first behaviour (reading the address being written returns the old word), that clk_en
low blocks writes and holds the whole read pipeline, the clk_en default (1) when unconnected,
and InitFile loading.

Words are undefined until written (or loaded from InitFile) and cL_rd_data_o is undefined
until the first enabled read reaches it, so the model tracks those values as unknown and
skips checking them. Verilator is 2-state, so the X itself is not observable here.
"""

import random
from collections import deque
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer

from tb_lib import mask, params, start_clock

P = params()
ADDR_WIDTH = P.get("AddrWidth", 12)
WIDTH = P.get("Width", 9)
OUTPUT_REG = P.get("OutputReg", 0)
CONNECT_CLK_EN = P.get("ConnectClkEn", 1)
USE_INIT_FILE = P.get("UseInitFile", 0)
DEPTH = 1 << ADDR_WIDTH
LATENCY = 1 + OUTPUT_REG
INIT_FILE = Path(__file__).parent / "ram_sp_init.hex"
NUM_VERIFY_CYCLES = 1000
STALL_PROBABILITY = 0.25
WRITE_PROBABILITY = 0.5
RAND_SEED = 0xDEAD_BEEF


class RamModel:
    """Reference model: DEPTH words, read-first, reads returned LATENCY enabled cycles later.

    Unknown words and unknown outputs are None. An unconnected clk_en takes its RTL default
    of 1, so the value driven on its pin is ignored.
    """

    def __init__(self, contents=None):
        self.mem = dict(contents or {})
        self.reads = deque([None] * LATENCY, maxlen=LATENCY)

    def clock(self, clk_en, wr_en, addr, data):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        if not clk_en:
            return
        self.reads.appendleft(self.mem.get(addr))
        if wr_en:
            self.mem[addr] = data

    @property
    def rd_data(self):
        return self.reads[-1]


def load_init_file():
    """Words of INIT_FILE in address order, as $readmemh reads them"""
    words = []
    for line in INIT_FILE.read_text().splitlines():
        words += [int(tok, 16) for tok in line.split("//")[0].split()]
    return words


async def step(dut, model, clk_en, wr_en, addr, data, ctx):
    """Drive one cycle, clock the model, and check cL_rd_data_o after the edge.

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
    result = int(dut.cL_rd_data_o.value)
    assert result == model.rd_data, (
        f"(AW={ADDR_WIDTH}, W={WIDTH}, L={LATENCY}, clk_en={'on' if CONNECT_CLK_EN else 'off'}) "
        f"{ctx} [clk_en={clk_en} we={wr_en} addr=0x{addr:x} wdata=0x{data:x}]: "
        f"got 0x{result:x}, expected 0x{model.rd_data:x}"
    )
    return result


async def drain(dut, model, ctx):
    """Clock LATENCY enabled reads of address 0 so every earlier read reaches the output"""
    return [await step(dut, model, 1, 0, 0, 0, f"{ctx} drain {i}") for i in range(LATENCY)]


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
    await drain(dut, model, "final")


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
    await drain(dut, model, "final")


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
        outputs = [
            await step(dut, model, 1, 1, addr, old, f"trial {trial} write old"),
            await step(dut, model, 1, 1, addr, new, f"trial {trial} write new"),
            await step(dut, model, 1, 0, addr, 0, f"trial {trial} read back"),
        ]
        outputs += await drain(dut, model, f"trial {trial}")

        # The read issued on step i reaches the output on step i + LATENCY - 1
        during_write = outputs[1 + LATENCY - 1]
        after_write = outputs[2 + LATENCY - 1]
        assert during_write == old, (
            f"(L={LATENCY}) trial {trial}: write cycle returned 0x{during_write:x}, expected old 0x{old:x}"
        )
        assert after_write == new, (
            f"(L={LATENCY}) trial {trial}: read back 0x{after_write:x}, expected new 0x{new:x}"
        )


@cocotb.test(skip=not CONNECT_CLK_EN)
async def test_clk_en_stall(dut):
    """With clk_en low, writes are ignored and the read pipeline holds while the inputs change"""
    start_clock(dut.clk)
    random.seed(RAND_SEED)
    model = RamModel()

    a, b = random.sample(range(DEPTH), 2)
    word_a = random.randint(0, mask(WIDTH))
    await step(dut, model, 1, 1, a, word_a, "write a")
    await step(dut, model, 1, 1, b, word_a ^ mask(WIDTH), "write b")
    await step(dut, model, 1, 0, a, 0, "read a")
    # With OutputReg, word a is at the output and b is still in flight when the stall starts
    held = await step(dut, model, 1, 0, b, 0, "read b")

    # Ending on a means a read of b lost from the pipeline would come back as word a
    for cycle, addr in enumerate((b, a, b, a)):
        result = await step(dut, model, 0, 1, addr, random.randint(0, mask(WIDTH)), f"stall {cycle}")
        assert result == held, f"stall {cycle}: output changed 0x{held:x} -> 0x{result:x}"

    # Resuming delivers the read still in flight, then the pre-stall words: stalled writes never landed
    await step(dut, model, 1, 0, a, 0, "resume read a")
    await step(dut, model, 1, 0, b, 0, "resume read b")
    await drain(dut, model, "final")


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
