"""Shared helpers for rtl-lib cocotb testbenches."""

import os

from cocotb.clock import Clock

CLK_PERIOD_NS = 4


def params():
    """Active parameter set from the Makefile, e.g. TB_PARAMS="Width=8,Depth=3" -> {"Width": 8, "Depth": 3}."""
    result = {}
    for item in filter(None, os.environ.get("TB_PARAMS", "").split(",")):
        name, value = item.split("=", 1)
        result[name] = int(value, 0)
    return result


def start_clock(clk, period_ns=CLK_PERIOD_NS):
    Clock(clk, period_ns, unit="ns").start()


def mask(width):
    return (1 << width) - 1
