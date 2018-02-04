#!/bin/bash
# Requires snakefood and graphviz installed
# sudo apt install snakefood graphviz
sfood -i -r -I tests ../ > pytomation.deps;
sfood-graph -r pytomation.deps > pytomation.deps.gv;
dot -Tps -opytomation.deps.ps pytomation.deps.gv;
