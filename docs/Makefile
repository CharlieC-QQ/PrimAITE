# © Crown-owned copyright 2025, Defence Science and Technology Laboratory UK
# Minimal makefile for Sphinx documentation
# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

AUTOSUMMARY="source/_autosummary"
NOTEBOOKS="source/notebooks/notebooks"

# Remove command is different depending on OS
ifdef OS
	RM = IF exist $(AUTOSUMMARY) (RMDIR $(AUTOSUMMARY) /s /q) & IF exist $(NOTEBOOKS) (RMDIR $(NOTEBOOKS) /s /q)
else
   ifeq ($(shell uname), Linux)
      RM = rm -rf $(AUTOSUMMARY) $(NOTEBOOKS)
   endif
endif


# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

clean:
	$(RM)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile | clean

	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
