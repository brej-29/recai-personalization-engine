# Reproduce every number from raw pulls. Raw data is not redistributed; see docs/DATA.md.
.PHONY: fetch catalog embed eval ml web-data reproduce test

fetch:
	uv run python -m kindred.fetch_anilist
	uv run python -m kindred.fetch_wiki

catalog:
	uv run python -m kindred.build_catalog
	uv run python -m kindred.stats

embed:
	uv run python -m kindred.embed minilm bge-small gte-small qwen3-0.6b

eval:
	uv run python -m kindred.eval.run_xm
	uv run python -m kindred.eval.run_xm --final

ml:
	uv run python -m kindred.eval.run_ml

web-data:
	uv run python -m kindred.export_web
	uv run python -m kindred.export_evidence

reproduce: fetch catalog embed eval ml web-data

test:
	uv run pytest
	cd web && npm test
