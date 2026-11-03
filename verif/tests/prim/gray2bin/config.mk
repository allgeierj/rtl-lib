VERILOG_SOURCES = \
	$(RTL_DIR)/prim/gray2bin.sv \
	$(TEST_DIR)/gray2bin_tb.sv

COCOTB_TOPLEVEL = gray2bin_tb
COCOTB_TEST_MODULES = test_gray2bin

PARAM_SETS = \
	Width=1 \
	Width=2 \
	Width=3 \
	Width=8 \
	Width=16 \
	Width=32 \
	Width=64 \
	Width=128
