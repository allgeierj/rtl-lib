VERILOG_SOURCES = \
	$(RTL_DIR)/mem/ram_sp.sv \
	$(TEST_DIR)/ram_sp_tb.sv

COCOTB_TOPLEVEL = ram_sp_tb
COCOTB_TEST_MODULES = test_ram_sp

# UseInitFile=1 needs AddrWidth=4,Width=8 to match ram_sp_init.hex
PARAM_SETS = \
	AddrWidth=1,Width=1 \
	AddrWidth=4,Width=8 \
	AddrWidth=12,Width=9 \
	AddrWidth=6,Width=72 \
	AddrWidth=14,Width=32 \
	AddrWidth=1,Width=1,ConnectClkEn=0 \
	AddrWidth=4,Width=8,ConnectClkEn=0 \
	AddrWidth=4,Width=8,UseInitFile=1 \
	AddrWidth=1,Width=1,OutputReg=1 \
	AddrWidth=12,Width=9,OutputReg=1 \
	AddrWidth=6,Width=72,OutputReg=1 \
	AddrWidth=4,Width=8,OutputReg=1,ConnectClkEn=0 \
	AddrWidth=4,Width=8,OutputReg=1,UseInitFile=1

COMPILE_ARGS += +define+RAM_SP_INIT_FILE=\"$(TEST_DIR)/ram_sp_init.hex\"
