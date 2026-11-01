VERILOG_SOURCES = \
	$(RTL_DIR)/prim/bin2gray.sv \
	$(TEST_DIR)/bin2gray_tb.sv

COCOTB_TOPLEVEL = bin2gray_tb
COCOTB_TEST_MODULES = test_bin2gray

PARAM_SETS = \
	Width=1 \
	Width=2 \
	Width=3 \
	Width=8 \
	Width=16 \
	Width=32 \
	Width=64 \
	Width=128
