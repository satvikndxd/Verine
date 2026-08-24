PY ?= python
VENVPY ?= .venv/bin/python

.PHONY: setup api web test e2e e2e-link benchmark demo clean

setup:
	python3 -m venv .venv && .venv/bin/pip install -e backend[dev]
	cd apps/web && npm install

api:
	cd apps/api && ../../.venv/bin/python -m uvicorn main:app --port 8000

web:
	cd apps/web && npm run dev

test:
	$(VENVPY) -m pytest tests/unit tests/simulation tests/replay tests/api -q

e2e-link:
	@test -e tests/e2e/node_modules || ln -s ../../apps/web/node_modules tests/e2e/node_modules

e2e: e2e-link
	cd apps/web && npx playwright test

benchmark:
	$(VENVPY) -m verine.cli benchmark --out research/benchmark/engineering_benchmark_v0_1.json

demo:
	$(VENVPY) -m verine.cli fixture run

clean:
	rm -rf data .pytest_cache apps/web/.next
