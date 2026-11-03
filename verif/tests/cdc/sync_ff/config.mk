VERILOG_SOURCES = \
	$(RTL_DIR)/cdc/sync_ff.sv \
	$(TEST_DIR)/sync_ff_tb.sv

COCOTB_TOPLEVEL = sync_ff_tb
COCOTB_TEST_MODULES = test_sync_ff

PARAM_SETS = \
	Width=1,Stages=2 \
	Width=1,Stages=3 \
	Width=8,Stages=2 \
	Width=32,Stages=4 \
	Width=64,Stages=8
