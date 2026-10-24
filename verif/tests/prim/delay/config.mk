VERILOG_SOURCES = \
	$(RTL_DIR)/prim/delay.sv \
	$(TEST_DIR)/delay_tb.sv

COCOTB_TOPLEVEL = delay_tb
COCOTB_TEST_MODULES = test_delay

PARAM_SETS = \
	Width=1,Depth=0 \
	Width=1,Depth=1 \
	Width=8,Depth=3 \
	Width=32,Depth=16 \
	Width=64,Depth=64

COMPILE_ARGS += -Wno-ASCRANGE
