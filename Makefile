.PHONY: test demo web verify
test:
	python3 -m pytest -q
demo:
	PYTHONPATH=src python3 -m sceneproof.cli demo
web:
	PYTHONPATH=src python3 -m sceneproof.web --port 8000
verify: test demo
	PYTHONPATH=src python3 -m sceneproof.web --smoke --port 8766
