"""Shared test helpers."""

import json
import pathlib
import tempfile


def write_and_load_json(module, draws):
    """
    Call module.write_json(draws) in an isolated temp directory and return
    the parsed JSON data as a Python object.

    Patches module.RESULTS_JSON for the duration of the call, then restores
    the original.
    """
    with tempfile.TemporaryDirectory() as tmp:
        json_path = pathlib.Path(tmp) / "results.json"
        orig_json = module.RESULTS_JSON
        module.RESULTS_JSON = json_path
        try:
            module.write_json(draws)
            with open(json_path, encoding="utf-8") as f:
                return json.load(f)
        finally:
            module.RESULTS_JSON = orig_json
