# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A library of reusable SystemVerilog modules in `rtl/<category>/`, each verified with cocotb (2.0.1) on Verilator. The
default simulator comes from `SIM ?= verilator` in `verif/Makefile`.

## Commands

`verif/Makefile` calls `cocotb-config`, so activate the venv first: `source .venv/bin/activate`.

```sh
make verif tc=delay                       # every PARAM_SETS entry for one test
make verif tc=delay P=Width=8,Depth=3     # one parameter set
make verif tc=delay WAVES=1               # also dump dump.fst into each build dir
make regress                              # all tests, with a PASS/FAIL summary
make -C verif list                        # available tests
make -C verif clean                       # remove build outputs

# One test case from one parameter set
COCOTB_TEST_FILTER=test_walking_one make verif tc=bin2gray P=Width=8
```

Build outputs go to `verif/work/<test>/<params>/`, one directory per parameter set.

## How the verif environment works

- **Discovery:** `verif/Makefile` finds tests with the glob `tests/*/*/config.mk`, and `tc` is the module directory
  name. A new directory with a `config.mk` joins `make regress` with no registration step.
- **Parameters:** each `PARAM_SETS` entry is passed two ways. It reaches the simulation as Verilator `-G` overrides on
  the `_tb` wrapper's parameters, and reaches Python as `TB_PARAMS`, which `tb_lib.params()` parses into a dict.
- **`tb_lib` helpers:** `params()`, `start_clock()` (4 ns period) and `mask(width)`. Use these rather than redefining
  them in a test.

## Adding tests for a module

Every module gets exactly these three files in `verif/tests/<category>/<module>/`. Use the closest existing test as the
template:

| New module is | Template |
|---|---|
| Purely combinational | `verif/tests/prim/bin2gray/` |
| Clocked, with `clk_en`/`rst` | `verif/tests/prim/edge_detect/` or `verif/tests/prim/delay/` |
| Built from other library modules | `verif/tests/prim/delay_valid/` |

### `config.mk`

Defines `VERILOG_SOURCES`, `COCOTB_TOPLEVEL` (`<module>_tb`), `COCOTB_TEST_MODULES` (`test_<module>`) and `PARAM_SETS`.

- `VERILOG_SOURCES` lists the wrapper plus every RTL file the module needs, including submodules, using `$(RTL_DIR)`
  and `$(TEST_DIR)`.
- `PARAM_SETS` entries are space-separated and comma-joined inside an entry, with no spaces: `Width=8,ConnectRst=0`.
- Cover the smallest legal values (`Width=1`, `Depth=0`), typical and large sizes, and for clocked modules, sets with
  `ConnectRst=0` and/or `ConnectClkEn=0`.
- Add Verilator flags as `COMPILE_ARGS +=` here. The `delay` tests need `-Wno-ASCRANGE`.

### `<module>_tb.sv`

A thin wrapper with no logic, named `<module>_tb`, always present even when the DUT's parameters could be set directly.

- Exposes only `int`/`bit` parameters, because `-G` can't set a `type` parameter. Map them onto the DUT, such as
  `.DataType(logic [Width-1:0])`.
- For a module with `clk_en`/`rst` port defaults, add `ConnectRst` and `ConnectClkEn` parameters and four `g_dut`
  generate branches that omit those ports. The wrapper keeps both pins in every branch, so Python can always drive them
  and confirm that an unconnected pin has no effect.
- Name the instance `u_<module>`, and use `.name` implicit port connections.

### `test_<module>.py`

Laid out in this order:

1. A module docstring stating what is verified, plus any interpretation of the spec the model relies on.
2. Module-level constants: `P = params()`, then `WIDTH = P.get("Width", 8)` and so on, followed by `NUM_VERIFY_CYCLES`,
   `RESET_PROBABILITY`, `STALL_PROBABILITY` and `RAND_SEED = 0xDEAD_BEEF` where they apply. `P.get` defaults must match
   the `_tb.sv` parameter defaults, because a `P=` value can leave parameters unset.
3. A reference model class, when the module has state, with a `clock(...)` method and expected outputs. Apply RTL
   defaults for unconnected ports inside the model: `clk_en if CONNECT_CLK_EN else 1`, `rst if CONNECT_RST else 0`.
4. Helpers such as `step()`, `check()` and `read_outputs()`.
5. `@cocotb.test()` coroutines, each with a one-line docstring.

Test behaviour:

- **Write the model from the module's documented behaviour,** not by copying the RTL expression, so that it can
  disagree with the RTL.
- **Parameter-dependent tests** use `skip=`, such as `@cocotb.test(skip=DEPTH == 0 or not CONNECT_RST)`, instead of
  branching inside the test.
- **Test order matters.** All tests in a file share one simulation, so state carries over and reset-value or power-up
  tests must come first, before any clock starts. Mark them `(must run first)` in the docstring. Later tests flush or
  prime the DUT so it agrees with a fresh model (`flush()` in `delay`, `prime()` in `edge_detect`).
- **Timing:** drive inputs, `await RisingEdge(dut.clk)`, then `await Timer(1, unit="ns")` before reading outputs. For
  combinational outputs, drive, then `await Timer(1, unit="ns")`. cocotb 2.0 uses `unit=`, not `units=`.
- **Clocks:** call `start_clock(dut.clk)` in each clocked test. Purely combinational modules have no clock.
- **Randomness:** call `random.seed(RAND_SEED)` at the start of each test that uses it. Random tests run
  `NUM_VERIFY_CYCLES` iterations and vary `clk_en` and `rst` alongside the data.
- **Combinational modules:** cover every input up to a width cap, then corners plus random values (see
  `EXHAUSTIVE_MAX_WIDTH` in `test_bin2gray.py`).
- **Assertion messages** include the active parameters, the cycle or context and hex values:
  `f"(W={WIDTH}) cycle {cycle}: got 0x{result:x}, expected 0x{expected:x}"`.
- **Reuse coverage:** a wrapper module's tests focus on what it adds. `delay_valid` leaves shift and stall behaviour to
  the `delay` tests.

### After adding a module

Add a row to the module table in `README.md`, with parameters and their limits, inputs and outputs. Place it next to
related modules rather than alphabetically, so pairs like `bin2gray` and `gray2bin` stay together. Then run
`make regress`.

## RTL conventions

- Signal names carry a cycle prefix: `c0_` is the input cycle, `cX_` is an output some cycles later, and a `c0_` output
  is combinational from the current inputs. Ports also end in `_i` or `_o`.
- `clk_en` defaults to `1'b1` and `rst` (synchronous, active high) to `1'b0`, so either can be left unconnected.
- Clocked modules hold their state in a packed struct `<module>_state_ts` with `reg_d` and `reg_q = '0`, computed in
  `always_comb` and registered in `always_ff`, where `rst` is assigned after `clk_en` so that it takes priority.
- Validate parameters at elaboration: `if(Width < 1) $error("Width must be >= 1 (got %0d)", Width);`.
- Instantiate library modules rather than duplicating their logic, as `delay_valid` does with `delay`.
