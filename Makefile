.PHONY: docs-install docs-check docs-build docs-serve

docs-install:
	cd backend && uv sync --group docs

docs-check:
	cd backend && uv run --group docs python ../scripts/docs.py check

docs-build:
	cd backend && uv run --group docs python ../scripts/docs.py build

docs-serve:
	cd backend && uv run --group docs python ../scripts/docs.py serve
