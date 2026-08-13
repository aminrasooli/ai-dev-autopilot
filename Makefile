.PHONY: help sync generate status doctor test review manage unmanage remote deps clean

# The hub is the checkout this Makefile lives in, so `make status`, `make sync`
# and `make test` all act on the tree you are standing in rather than on
# whatever happens to be at ~/.ai-dev. For the documented install — cloning to
# ~/.ai-dev — the two are the same path. An explicit AI_DEV_HOME still wins, and
# it is exported so bin/* and tests/* resolve the same hub.
AI_DEV_HOME ?= $(patsubst %/,%,$(dir $(abspath $(lastword $(MAKEFILE_LIST)))))
export AI_DEV_HOME

help:
	@echo "AI-DEV — $(AI_DEV_HOME) is the source of truth."
	@echo
	@echo "  make sync       project the hub onto Claude, Codex and Qwen adapters"
	@echo "  make generate   rebuild generated/AGENTS.md from core/"
	@echo "  make status     show what is linked where"
	@echo "  make doctor     verify contracts and behaviour"
	@echo "  make test       run every contract test"
	@echo "  make review     Codex review of this hub's uncommitted changes"
	@echo "  make manage     deploy the managed enforcement floor (needs sudo)"
	@echo "  make unmanage   remove the managed enforcement floor (needs sudo)"
	@echo "  make remote     start Claude Remote Control here"
	@echo "  make deps       install sandbox dependencies (needs sudo)"

sync:      ; @bin/ai-dev sync
generate:  ; @bin/ai-dev generate
status:    ; @bin/ai-dev status
doctor:    ; @bin/doctor $(ARGS)
test:      ; @tests/run-all.sh
review:    ; @bin/codex-review $(ARGS)
manage:    ; @bin/ai-dev manage
unmanage:  ; @bin/ai-dev unmanage
remote:    ; @bin/ai-dev remote $(ARGS)

deps:
	sudo apt-get update && sudo apt-get install -y bubblewrap socat
	npm install -g @anthropic-ai/sandbox-runtime
	@echo "Restart Claude Code so it re-runs its dependency check."

clean:
	rm -rf var/guard.log
