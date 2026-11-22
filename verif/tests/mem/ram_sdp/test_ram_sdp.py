"""
cocotb tests for the ram_sdp module.

Verifies writes on wr_clk and reads on rd_clk with Latency = 1 + OutputReg rd_clk cycles,
writes to every address, that rd_c0_enable_i low keeps rd_cL_data_o on the last word read
while writes still land, that rd_clk_en low holds the read pipeline and wr_clk_en low blocks
writes, read-first behaviour with a shared clock, the clock enable defaults (1) when
unconnected, InitFile loading, and both ports running at once.

With separate clocks, rd_clk has a 4 ns period and wr_clk 6 ns, started 1 ns later, so their
edges never coincide. The model logs each write with its edge time and resolves a read against
the writes before its edge. A write to the same address on the same edge is read-first with a
shared clock and unknown with separate clocks. In hardware the separate-clock collision window
is wider than one instant, but RTL simulation is exact.

Words are undefined until written (or loaded from InitFile) and rd_cL_data_o is undefined until
the first read reaches it, so the model tracks those values as unknown and skips checking them.
Verilator is 2-state, so the X itself is not observable here.
"""

import random
from collections import deque
from pathlib import Path

import cocotb
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time

from tb_lib import mask, params, start_clock

P = params()
ADDR_WIDTH = P.get("AddrWidth", 12)
WIDTH = P.get("Width", 9)
OUTPUT_REG = P.get("OutputReg", 0)
SHARED_CLOCK = P.get("SharedClock", 0)
CONNECT_CLK_EN = P.get("ConnectClkEn", 1)
USE_INIT_FILE = P.get("UseInitFile", 0)
DEPTH = 1 << ADDR_WIDTH
LATENCY = 1 + OUTPUT_REG
WR_CLK_PERIOD_NS = 6
WR_CLK_OFFSET_NS = 1
INIT_FILE = Path(__file__).parent / "ram_sdp_init.hex"
NUM_VERIFY_CYCLES = 1000
STALL_PROBABILITY = 0.25
READ_PROBABILITY = 0.5
WRITE_PROBABILITY = 0.5
RAND_SEED = 0xDEAD_BEEF


class RamModel:
    """Reference model: DEPTH words, written on wr_clk, read LATENCY enabled rd_clk cycles later.

    A read returns the last write to its address before its edge. A write on the same edge is
    read-first with a shared clock and unknown with separate clocks. An enabled read cycle
    without a read repeats the previous read, so the output keeps the last word read. Unknown
    words and outputs are None. Unconnected clock enables take their RTL default of 1, so the
    values driven on their pins are ignored.
    """

    def __init__(self, contents=()):
        self.writes = {addr: [(float("-inf"), data)] for addr, data in contents}
        self.reads = deque([None] * LATENCY, maxlen=LATENCY)

    def write(self, time, clk_en, en, addr, data):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        if clk_en and en:
            self.writes.setdefault(addr, []).append((time, data))

    def word(self, addr, time):
        """Word that a read of addr on the rd_clk edge at time returns"""
        word = None
        for write_time, data in self.writes.get(addr, []):
            if write_time < time:
                word = data
            elif write_time == time and not SHARED_CLOCK:
                return None
        return word

    def read(self, time, clk_en, en, addr):
        clk_en = clk_en if CONNECT_CLK_EN else 1
        if not clk_en:
            return
        self.reads.appendleft(self.word(addr, time) if en else self.reads[0])

    @property
    def rd_data(self):
        return self.reads[-1]


def load_init_file():
    """Words of INIT_FILE in address order, as $readmemh reads them"""
    words = []
    for line in INIT_FILE.read_text().splitlines():
        words += [int(tok, 16) for tok in line.split("//")[0].split()]
    return words


def idle(dut):
    """Both ports enabled, neither reading nor writing"""
    dut.rd_clk_en.value = 1
    dut.wr_clk_en.value = 1
    dut.rd_c0_enable_i.value = 0
    dut.wr_c0_enable_i.value = 0


def wr_clk(dut):
    """Clock the DUT's write port runs on: rd_clk when the ports share a clock"""
    return dut.rd_clk if SHARED_CLOCK else dut.wr_clk


async def start_clocks(dut):
    """Start rd_clk and, unless the ports share a clock, wr_clk offset so no edges coincide"""
    start_clock(dut.rd_clk)
    if not SHARED_CLOCK:
        await Timer(WR_CLK_OFFSET_NS, unit="ns")
        start_clock(dut.wr_clk, WR_CLK_PERIOD_NS)


async def wr_step(dut, model, clk_en, en, addr, data):
    """Drive one write-port cycle and log it in the model; the write enable drops after the edge"""
    dut.wr_clk_en.value = clk_en
    dut.wr_c0_enable_i.value = en
    dut.wr_c0_address_i.value = addr
    dut.wr_c0_data_i.value = data
    await RisingEdge(wr_clk(dut))
    model.write(get_sim_time(), clk_en, en, addr, data)
    dut.wr_c0_enable_i.value = 0
    await Timer(1, unit="ns")


async def rd_step(dut, model, clk_en, en, addr, ctx):
    """Drive one read-port cycle, clock the model, and check rd_cL_data_o after the edge.

    The read enable drops after the edge, so the port idles between steps. Returns the output,
    or None when the model says it is unknown.
    """
    dut.rd_clk_en.value = clk_en
    dut.rd_c0_enable_i.value = en
    dut.rd_c0_address_i.value = addr
    await RisingEdge(dut.rd_clk)
    time = get_sim_time()
    dut.rd_c0_enable_i.value = 0
    await Timer(1, unit="ns")

    model.read(time, clk_en, en, addr)
    if model.rd_data is None:
        return None
    result = int(dut.rd_cL_data_o.value)
    assert result == model.rd_data, (
        f"(AW={ADDR_WIDTH}, W={WIDTH}, L={LATENCY}, {'shared' if SHARED_CLOCK else 'separate'} clocks, "
        f"clk_en={'on' if CONNECT_CLK_EN else 'off'}) {ctx} "
        f"[rd_clk_en={clk_en} re={en} raddr=0x{addr:x}]: got 0x{result:x}, expected 0x{model.rd_data:x}"
    )
    return result


async def drain(dut, model, ctx):
    """Clock LATENCY enabled reads of address 0 so every earlier read reaches the output"""
    return [await rd_step(dut, model, 1, 1, 0, f"{ctx} drain {i}") for i in range(LATENCY)]


@cocotb.test(skip=not USE_INIT_FILE)
async def test_init_file(dut):
    """Every word reads back as loaded from InitFile (must run first, before any write)"""
    words = load_init_file()
    assert len(words) == DEPTH and max(words) <= mask(WIDTH), (
        f"{INIT_FILE.name} holds {len(words)} words up to 0x{max(words):x}, "
        f"which does not fit AW={ADDR_WIDTH}, W={WIDTH}"
    )
    idle(dut)
    await start_clocks(dut)
    model = RamModel(enumerate(words))

    for addr in range(DEPTH):
        await rd_step(dut, model, 1, 1, addr, f"read {addr}")
    await drain(dut, model, "final")


@cocotb.test()
async def test_write_read_all(dut):
    """A random word written to every address reads back, in shuffled order"""
    idle(dut)
    await start_clocks(dut)
    random.seed(RAND_SEED)
    model = RamModel()

    for addr in range(DEPTH):
        await wr_step(dut, model, 1, 1, addr, random.randint(0, mask(WIDTH)))

    order = list(range(DEPTH))
    random.shuffle(order)
    for addr in order:
        await rd_step(dut, model, 1, 1, addr, f"read {addr}")
    await drain(dut, model, "final")


@cocotb.test(skip=not SHARED_CLOCK)
async def test_read_first(dut):
    """With a shared clock, reading the address being written returns the old word"""
    idle(dut)
    await start_clocks(dut)
    random.seed(RAND_SEED)
    model = RamModel()

    for trial in range(8):
        addr = random.randrange(DEPTH)
        old = random.randint(0, mask(WIDTH))
        new = old ^ mask(WIDTH)
        await wr_step(dut, model, 1, 1, addr, old)
        # Both ports on the same edge: write new while reading the same address
        write = cocotb.start_soon(wr_step(dut, model, 1, 1, addr, new))
        outputs = [await rd_step(dut, model, 1, 1, addr, f"trial {trial} read during write")]
        await write
        outputs.append(await rd_step(dut, model, 1, 1, addr, f"trial {trial} read back"))
        outputs += await drain(dut, model, f"trial {trial}")

        # The read issued on step i reaches the output on step i + LATENCY - 1
        during_write = outputs[LATENCY - 1]
        after_write = outputs[LATENCY]
        assert during_write == old, (
            f"(L={LATENCY}) trial {trial}: read during write returned 0x{during_write:x}, expected old 0x{old:x}"
        )
        assert after_write == new, (
            f"(L={LATENCY}) trial {trial}: read back 0x{after_write:x}, expected new 0x{new:x}"
        )


@cocotb.test()
async def test_rd_enable(dut):
    """With rd_c0_enable_i low, rd_cL_data_o keeps the last word read while writes still land"""
    idle(dut)
    await start_clocks(dut)
    random.seed(RAND_SEED)
    model = RamModel()

    a, b = random.sample(range(DEPTH), 2)
    word_a = random.randint(0, mask(WIDTH))
    other = word_a ^ mask(WIDTH)
    await wr_step(dut, model, 1, 1, a, word_a)
    await wr_step(dut, model, 1, 1, b, other)
    await rd_step(dut, model, 1, 1, b, "read b")
    # A single-cycle read: with OutputReg, word a must still reach the output after rd_en drops
    await rd_step(dut, model, 1, 1, a, "read a")

    # Overwrite both words with `other` and point the read address at each: a read would return it
    for cycle, addr in enumerate((b, a)):
        await wr_step(dut, model, 1, 1, addr, other)
        for raddr in (b, a):
            result = await rd_step(dut, model, 1, 0, raddr, f"no read {cycle}")
            assert result == word_a, (
                f"(L={LATENCY}) no read {cycle}: got 0x{result:x}, expected last read 0x{word_a:x}"
            )

    # The writes made while rd_en was low landed
    await rd_step(dut, model, 1, 1, a, "read back a")
    await rd_step(dut, model, 1, 1, b, "read back b")
    await drain(dut, model, "final")


@cocotb.test(skip=not CONNECT_CLK_EN)
async def test_clk_en_stall(dut):
    """With rd_clk_en low the read pipeline holds while its inputs change, and wr_clk_en low blocks writes"""
    idle(dut)
    await start_clocks(dut)
    random.seed(RAND_SEED)
    model = RamModel()

    a, b = random.sample(range(DEPTH), 2)
    word_a = random.randint(0, mask(WIDTH))
    words = {a: word_a, b: word_a ^ mask(WIDTH)}
    for addr, word in words.items():
        await wr_step(dut, model, 1, 1, addr, word)
    await rd_step(dut, model, 1, 1, a, "read a")
    # With OutputReg, word a is at the output and b is still in flight when the stall starts
    held = await rd_step(dut, model, 1, 1, b, "read b")

    # Ending on a means a read of b lost from the pipeline would come back as word a. The read
    # stall comes first in each cycle, so the read port never idles with rd_clk_en high.
    for cycle, addr in enumerate((b, a, b, a)):
        result = await rd_step(dut, model, 0, 1, addr, f"stall {cycle}")
        assert result == held, f"(L={LATENCY}) stall {cycle}: output changed 0x{held:x} -> 0x{result:x}"
        await wr_step(dut, model, 0, 1, addr, words[addr] ^ mask(WIDTH))

    # Resuming delivers the read still in flight, then the pre-stall words: stalled writes never landed
    await rd_step(dut, model, 1, 1, a, "resume read a")
    await rd_step(dut, model, 1, 1, b, "resume read b")
    await drain(dut, model, "final")


@cocotb.test()
async def test_random(dut):
    """Random reads and writes on both ports at once, with random clock enables, against the model.

    Addresses mostly come from a small pool so reads often hit recent writes. When the clock
    enables are unconnected, the random values on their pins must have no effect.
    """
    idle(dut)
    await start_clocks(dut)
    random.seed(RAND_SEED)
    model = RamModel()
    pool = random.sample(range(DEPTH), min(DEPTH, 16))
    done = False

    def pick_addr():
        return random.choice(pool) if random.random() < 0.9 else random.randrange(DEPTH)

    async def writer():
        while not done:
            clk_en = int(random.random() >= STALL_PROBABILITY)
            en = int(random.random() < WRITE_PROBABILITY)
            await wr_step(dut, model, clk_en, en, pick_addr(), random.randint(0, mask(WIDTH)))

    write_task = cocotb.start_soon(writer())
    for cycle in range(NUM_VERIFY_CYCLES):
        clk_en = int(random.random() >= STALL_PROBABILITY)
        en = int(random.random() < READ_PROBABILITY)
        await rd_step(dut, model, clk_en, en, pick_addr(), f"cycle {cycle}")
    done = True
    await write_task
