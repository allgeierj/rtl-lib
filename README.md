# rtl-lib

A work-in-progress library of common, reusable SystemVerilog modules, each verified with a
[cocotb](https://www.cocotb.org/) testbench. It currently covers a few basic primitives; more
modules, categories and tests will be added over time, and existing interfaces may still change.

## Layout

```
rtl/
  prim/                 basic primitives (delay lines, edge detection, ...)
verif/
  Makefile              cocotb test runner
  tb_lib/               shared Python helpers for testbenches
  tests/<category>/<module>/
    config.mk           sources, toplevel and the parameter sets to sweep
    <module>_tb.sv      thin wrapper mapping int params onto the DUT
    test_<module>.py    cocotb tests
```

## Conventions

- Signal names carry a cycle prefix: `c0_` is the input cycle, `cX_` is an output some number
  of cycles later, and a `c0_` output is combinational from the current inputs.
- `clk_en` defaults to `1'b1` and `rst` (synchronous, active high) defaults to `1'b0`, so either
  can be left unconnected.

## Modules

### `prim`

| Module | Description | Parameters | Inputs | Outputs |
|---|---|---|---|---|
| [`delay`](rtl/prim/delay.sv) | Delays data by `Depth` enabled cycles; combinational when `Depth == 0`. Leave `rst` unconnected to keep SRL inference. | `type DataType = logic`<br>`int Depth = 1` (>= 0) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`DataType c0_data_i` | `DataType cX_data_o` |
| [`delay_valid`](rtl/prim/delay_valid.sv) | Delays a valid/data pair together by `Depth` enabled cycles. `rst` clears only the valid line, so data still maps to SRLs. | `type DataType = logic`<br>`int Depth = 1` (>= 0) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`c0_valid_i`<br>`DataType c0_data_i` | `cX_valid_o`<br>`DataType cX_data_o` |
| [`edge_detect`](rtl/prim/edge_detect.sv) | Per-bit rising/falling/either edge pulses, valid when `c0_valid_o` is high. The first enabled sample after power-up or `rst` only arms the detector. | `int Width = 1` (>= 1) | `clk`<br>`clk_en = 1`<br>`rst = 0`<br>`[Width-1:0] c0_detect_i` | `c0_valid_o`<br>`[Width-1:0] c0_rising_o`<br>`[Width-1:0] c0_falling_o`<br>`[Width-1:0] c0_either_o` |

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
