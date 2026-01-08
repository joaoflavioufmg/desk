# desk/__main__.py

import argparse
import importlib.util
import sys
from pathlib import Path


def load_model_from_file(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"Model file not found: {path}")

    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def run_model(module):
    if hasattr(module, "run_simulation"):
        module.run_simulation()
    elif hasattr(module, "build_model"):
        model = module.build_model()
        model.run_simulation()
    else:
        raise RuntimeError(
            "Model must define either `run_simulation()` or `build_model()`"
        )


def main():
    parser = argparse.ArgumentParser(
        description="DESK – Discrete Event Simulation Kit"
    )
    parser.add_argument(
        "-m", "--model",
        required=True,
        help="Path to a DESK simulation model (.py)"
    )

    args = parser.parse_args()
    model_path = Path(args.model).resolve()

    module = load_model_from_file(model_path)
    run_model(module)


if __name__ == "__main__":
    main()
