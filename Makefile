# Convenience wrappers; see verif/Makefile.
.PHONY: verif regress

verif:
	$(MAKE) -C verif tc=$(tc) P=$(P) WAVES=$(WAVES)

regress:
	$(MAKE) -C verif regress WAVES=$(WAVES)
