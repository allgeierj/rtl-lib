VERILOG_SOURCES = \
	$(RTL_DIR)/prim/edge_detect.sv \
	$(TEST_DIR)/edge_detect_tb.sv

COCOTB_TOPLEVEL = edge_detect_tb
COCOTB_TEST_MODULES = test_edge_detect

PARAM_SETS = \
	Width=1 \
	Width=8 \
	Width=32 \
	Width=1,ConnectRst=0,ConnectClkEn=0 \
	Width=8,ConnectRst=0 \
	Width=8,ConnectClkEn=0
