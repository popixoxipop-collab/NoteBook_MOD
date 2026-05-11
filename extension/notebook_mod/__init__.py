from pathlib import Path

HERE = Path(__file__).parent.resolve()

with (HERE / "labextension" / "package.json").open() as f:
    import json
    data = json.load(f)

__version__ = data["version"]


def _jupyter_labextension_paths():
    return [{
        "src":  str(HERE / "labextension"),
        "dest": data["name"],
    }]
