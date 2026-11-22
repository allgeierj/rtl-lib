# rtl-lib

A work-in-progress library of common, reusable SystemVerilog modules, each verified with a
[cocotb](https://www.cocotb.org/) testbench. It currently covers a few basic primitives; more
modules, categories and tests will be added over time, and existing interfaces may still change.

## Layout

```
rtl/
  prim/                 basic primitives (delay lines, edge detection, ...)
  cdc/                  clock domain crossing (synchronisers, ...)
  mem/                  memories (RAMs, ...)
verif/
  Makefile              cocotb test runner
  tb_lib/               shared Python helpers for testbenches
  tests/<category>/<module>/
    config.mk           sources, toplevel and the parameter sets to sweep
    <module>_tb.sv      thin wrapper mapping int params onto the DUT
    test_<module>.py    cocotb tests
```

## Conventions

- Signal names carry a cycle prefix: `c0_` is the input cycle, `cL_` is an output some number
  of cycles later, and a `c0_` output is combinational from the current inputs.
- Modules with more than one clock put the clock domain before the cycle prefix: `rd_c0_address_i`
  is synchronous to `rd_clk` and counts `rd_clk` cycles. Single-clock modules use plain `clk`.
- `clk_en` defaults to `1'b1` and `rst` (synchronous, active high) defaults to `1'b0`, so either
  can be left unconnected.

## Modules

### `prim`

| Module | Description | Parameters | Inputs | Outputs |
|---|---|---|---|---|
| [`bin2gray`](rtl/prim/bin2gray.sv) | Combinational binary to reflected Gray code conversion. | `int Width = 8` (>= 1) | `[Width-1:0] c0_bin_i` | `[Width-1:0] c0_gray_o` |
| [`gray2bin`](rtl/prim/gray2bin.sv) | Combinational reflected Gray code to binary conversion; the inverse of `bin2gray`. | `int Width = 8` (>= 1) | `[Width-1:0] c0_gray_i` | `[Width-1:0] c0_bin_o` |
| [`delay`](rtl/prim/delay.sv) | Delays data by `Depth` enabled cycles; combinational when `Depth == 0`. Leave `rst` unconnected to keep SRL inference. | `type DataType = logic`<br>`int Depth = 1` (>= 0) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`DataType c0_data_i` | `DataType cL_data_o` |
| [`delay_valid`](rtl/prim/delay_valid.sv) | Delays a valid/data pair together by `Depth` enabled cycles. `rst` clears only the valid line, so data still maps to SRLs. | `type DataType = logic`<br>`int Depth = 1` (>= 0) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`c0_valid_i`<br>`DataType c0_data_i` | `cL_valid_o`<br>`DataType cL_data_o` |
| [`edge_detect`](rtl/prim/edge_detect.sv) | Per-bit rising/falling/either edge pulses, valid when `c0_valid_o` is high. The first enabled sample after power-up or `rst` only arms the detector. | `int Width = 1` (>= 1) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`[Width-1:0] c0_detect_i` | `c0_valid_o`<br>`[Width-1:0] c0_rising_o`<br>`[Width-1:0] c0_falling_o`<br>`[Width-1:0] c0_either_o` |

### `cdc`

| Module | Description | Parameters | Inputs | Outputs |
|---|---|---|---|---|
| [`sync_ff`](rtl/cdc/sync_ff.sv) | `Stages`-flop synchroniser into the `capture_clk` domain, with `ASYNC_REG` on every stage, powering up as zero. Bits are synchronised independently, so for `Width > 1` the data must be Gray-coded or otherwise change one bit at a time. `c0_data_i` should come straight from a source-domain register, and the input path needs a false-path or max-delay constraint. | `int Width = 1` (>= 1)<br>`int Stages = 2` (>= 2) | `capture_clk`<br>`[Width-1:0] c0_data_i` | `[Width-1:0] cL_data_o` |
| [`reset_sync`](rtl/cdc/reset_sync.sv) | Reset synchroniser: `rst_o` asserts asynchronously as soon as `async_rst_i` rises and deasserts `Stages` `clk` edges after it falls. Active high, `ASYNC_REG` on every stage, powering up asserted. `async_rst_i` should come from a register or pin, and its path to the stage presets needs a false-path constraint. | `int Stages = 2` (>= 2) | `clk`<br>`async_rst_i` | `rst_o` |

### `mem`

| Module | Description | Parameters | Inputs | Outputs |
|---|---|---|---|---|
| [`ram_sp`](rtl/mem/ram_sp.sv) | Single-port RAM of `2**$bits(AddressType)` words. Read latency is 1, or 2 with `OutputReg`, which maps onto the RAM primitive's output register (BRAM `DOA_REG`, URAM `OREG`). Read-first: reading the address being written returns the old word. With `c0_rd_enable_i` low, `cL_rd_data_o` keeps the last word read and writes still land. `clk_en` low blocks writes and holds the read pipeline. Words are undefined until written unless `InitFile` is set, and `cL_rd_data_o` is undefined until the first read reaches it. | `type AddressType = logic [11:0]`<br>`type DataType = logic [8:0]`<br>`bit OutputReg = 0`<br>`string InitFile = ""` (`$readmemh` hex)<br>`RamStyle = "block"` (Vivado `ram_style`; untyped, as Vivado rejects a `string` here) | `clk`<br>`clk_en = 1`<br>`c0_rd_enable_i`<br>`c0_wr_enable_i`<br>`AddressType c0_address_i`<br>`DataType c0_wr_data_i` | `DataType cL_rd_data_o` |
| [`ram_sdp`](rtl/mem/ram_sdp.sv) | Simple dual-port RAM of `2**$bits(AddressType)` words: writes on `wr_clk`, reads on `rd_clk`. Read latency is 1 `rd_clk` cycle, or 2 with `OutputReg`. With `rd_c0_enable_i` low, `rd_cL_data_o` keeps the last word read. `rd_clk_en` low holds the read pipeline and `wr_clk_en` low blocks writes. Reading the address being written returns the old word when both ports share a clock, and is undefined with separate clocks. Separate clocks rule out URAM (Vivado falls back to block RAM), and distributed RAM then needs a `wr_clk` to `rd_clk` timing constraint. Words are undefined until written unless `InitFile` is set, and `rd_cL_data_o` is undefined until the first read reaches it. | `type AddressType = logic [11:0]`<br>`type DataType = logic [8:0]`<br>`bit OutputReg = 0`<br>`string InitFile = ""` (`$readmemh` hex)<br>`RamStyle = "block"` (Vivado `ram_style`) | `rd_clk`<br>`rd_clk_en = 1`<br>`rd_c0_enable_i`<br>`AddressType rd_c0_address_i`<br>`wr_clk`<br>`wr_clk_en = 1`<br>`wr_c0_enable_i`<br>`AddressType wr_c0_address_i`<br>`DataType wr_c0_data_i` | `DataType rd_cL_data_o` |

## Running tests

Requires [Verilator](https://www.veripool.org/verilator/) and Python with the packages in
`verif/requirements.txt`:

```sh
pip install -r verif/requirements.txt
```

From the repo root (wrappers around `verif/Makefile`):

```sh
make verif tc=delay                     # run every parameter set for one test
make verif tc=delay P=Width=8,Depth=3   # run a single parameter set
make verif tc=delay WAVES=1             # also dump an FST waveform per build
make regress                            # run all tests and print a summary
```

`make -C verif list` shows the available tests. Build outputs go to `verif/work/<test>/<params>/`.

## Status

Early days — expect more primitives and higher-level building blocks to be added, along with
their tests.
