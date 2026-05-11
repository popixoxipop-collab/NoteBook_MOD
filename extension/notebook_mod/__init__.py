from pathlib import Path
from jupyter_server.utils import url_path_join

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


def _jupyter_server_extension_points():
    return [{"module": "notebook_mod"}]


def _load_jupyter_server_extension(server_app):
    from .handlers import AnalyzeHandler
    web_app      = server_app.web_app
    base_url     = web_app.settings.get("base_url", "/")
    route        = url_path_join(base_url, "notebook-mod", "analyze")
    web_app.add_handlers(".*$", [(route, AnalyzeHandler)])
    server_app.log.info(f"[NoteBook_MOD] analyze endpoint: {route}")
