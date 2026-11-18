VERILOG_SOURCES = \
	$(RTL_DIR)/cdc/reset_sync.sv \
	$(TEST_DIR)/reset_sync_tb.sv

COCOTB_TOPLEVEL = reset_sync_tb
COCOTB_TEST_MODULES = test_reset_sync

PARAM_SETS = \
	Stages=2 \
	Stages=3 \
	Stages=4 \
	Stages=8
