# cocotb test runner.
#
#   make tc=<test>                     run every PARAM_SETS entry for <test>
#   make tc=<test> P=Width=8,Depth=3   run a single parameter set
#   make tc=<test> WAVES=1             also dump dump.fst into each build dir
#   make regress                       run all tests, print a summary
#   make list | clean

SIM ?= verilator
TOPLEVEL_LANG ?= verilog

comma := ,
RTL_DIR := $(realpath ../rtl)
TESTS   := $(sort $(notdir $(patsubst %/,%,$(dir $(wildcard tests/*/*/config.mk)))))

.PHONY: list regress clean sweep

# A failed verilator run can leave a partial Vtop.mk that masks the error next time.
.DELETE_ON_ERROR:

ifndef tc

.DEFAULT_GOAL := usage
usage:
	@echo "Usage: make tc=<test> [P=Name=val,...] [WAVES=1] | make regress | make list | make clean"
	@exit 1

list:
	@printf '%s\n' $(TESTS)

regress:
	@fails=""; \
	for t in $(TESTS); do \
	  $(MAKE) --no-print-directory tc=$$t WAVES=$(WAVES) || fails="$$fails $$t"; \
	done; \
	echo; echo "==== regression summary ===="; \
	for t in $(TESTS); do \
	  case " $$fails " in *" $$t "*) echo "FAIL  $$t";; *) echo "PASS  $$t";; esac; \
	done; \
	[ -z "$$fails" ]

clean:
	rm -rf work results.xml

else

TEST_DIR := $(realpath $(dir $(wildcard tests/*/$(tc)/config.mk)))
ifeq ($(TEST_DIR),)
$(error No test '$(tc)' (expected tests/<category>/$(tc)/config.mk). Try 'make list')
endif

include $(TEST_DIR)/config.mk

ifneq ($(and $(PARAM_SETS),$(if $(P),,1)),)

# Outer make: re-invoke once per parameter set, keep going on failure.
.DEFAULT_GOAL := sweep
sweep:
	@fails=""; \
	for p in $(PARAM_SETS); do \
	  echo "==== $(tc) [$$p] ===="; \
	  $(MAKE) --no-print-directory tc=$(tc) P=$$p WAVES=$(WAVES) || fails="$$fails $$p"; \
	done; \
	if [ -n "$$fails" ]; then echo "$(tc) FAILED param sets:$$fails"; exit 1; fi

else

# Inner make: a single cocotb build/run.
BUILD_NAME := $(or $(subst =,-,$(subst $(comma),_,$(P))),default)$(if $(filter 1,$(WAVES)),_waves)
SIM_BUILD  := work/$(tc)/$(BUILD_NAME)
COCOTB_RESULTS_FILE := $(SIM_BUILD)/results.xml

COMPILE_ARGS += $(addprefix -G,$(subst $(comma), ,$(P)))

ifeq ($(WAVES),1)
COMPILE_ARGS += --trace-fst --trace-structs
SIM_ARGS     += --trace --trace-file $(SIM_BUILD)/dump.fst
endif

export TB_PARAMS := $(P)
export PYTHONPATH := $(TEST_DIR):$(CURDIR):$(PYTHONPATH)

include $(shell cocotb-config --makefiles)/Makefile.sim

endif
endif
