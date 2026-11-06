SHELL := /bin/bash
SUBSET ?= 0
VERSION ?= v1
PY ?= python3

.PHONY: up down train train-all eval lint test clean-data package report

up:            ## build and deploy everything from a fresh clone
	bash scripts/up.sh

down:          ## delete the cluster
	k3d cluster delete cmdparser

train:         ## fine-tune Pythia-70M (reads training/config.yaml); SUBSET=50 for a smoke test
	$(PY) -m training.train --version $(VERSION) $(if $(filter-out 0,$(SUBSET)),--subset $(SUBSET),)

train-all:
	$(MAKE) train VERSION=v1
	$(MAKE) train VERSION=v2

clean-data:    ## offline cleaning of downloaded shards: make clean-data SHARDS=results/teacher
	$(PY) -m worker.clean --local $(SHARDS) --out data

lint:
	ruff check .

test:
	$(PY) -m pytest -q

report:        ## rebuild report/report.pdf from report/report.md
	bash scripts/build_report.sh
