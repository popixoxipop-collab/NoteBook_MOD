"""Resolve package versions from manifest files and annotate import nodes.

D4: manifest-based version annotation
  WHY: version 정보 없이는 의존성 그래프가 "무엇을 쓰는가"만 보여줌.
       버전까지 표시해야 "같은 라이브러리를 서로 다른 버전으로 쓰는 파일이 있는가"를 감지 가능.
  COST: 정확도는 best-effort — lockfile이 아닌 선언 파일 파싱이므로 범위 지정(>=1.0)이 남을 수 있음.
  EXIT: pip-tools/poetry.lock/yarn.lock 파싱으로 교체하면 exact version 확보 가능.
"""
import json
import re
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "dist", "build"}


def _walk(root: Path):
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def _parse_requirements(path: Path) -> dict[str, str]:
    """requirements.txt / requirements-dev.txt"""
    out = {}
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = re.match(r"^([\w\-\.]+)\s*([=<>!~^,\s]+[\w\.\*]+)?", line)
        if m:
            pkg = m.group(1).lower().replace("-", "_")
            ver = (m.group(2) or "").strip() or "?"
            out[pkg] = ver
    return out


def _parse_pyproject(path: Path) -> dict[str, str]:
    """pyproject.toml — simple regex, no full TOML parse."""
    out = {}
    content = path.read_text(errors="replace")
    # [tool.poetry.dependencies] or [project] dependencies
    for m in re.finditer(r'"?([\w\-\.]+)"?\s*=\s*["\^~]?([\w\.\*,\s>=<!]+)"?', content):
        pkg = m.group(1).lower().replace("-", "_")
        ver = m.group(2).strip()
        if pkg not in ("python", "name", "version", "description"):
            out.setdefault(pkg, ver)
    return out


def _parse_package_json(path: Path) -> dict[str, str]:
    """package.json — dependencies / devDependencies / peerDependencies"""
    out = {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return out
    for section in ("dependencies", "devDependencies", "peerDependencies"):
        for pkg, ver in data.get(section, {}).items():
            out.setdefault(pkg, ver)
    return out


def _parse_pom_xml(path: Path) -> dict[str, str]:
    """pom.xml — <artifactId> + <version> pairs."""
    out = {}
    content = path.read_text(errors="replace")
    for m in re.finditer(
        r"<artifactId>([\w\-\.]+)</artifactId>.*?<version>([^<]+)</version>",
        content, re.DOTALL
    ):
        out.setdefault(m.group(1), m.group(2).strip())
    return out


def _parse_gradle(path: Path) -> dict[str, str]:
    """build.gradle — implementation 'group:artifact:version'"""
    out = {}
    for m in re.finditer(
        r"['\"][\w\.\-]+:([\w\.\-]+):([\w\.\-]+)['\"]",
        path.read_text(errors="replace")
    ):
        out.setdefault(m.group(1), m.group(2))
    return out


def resolve_versions(root: Path) -> dict[str, str]:
    """Scan root for manifest files; return {normalized_pkg_name: version_spec}."""
    versions: dict[str, str] = {}

    parsers = {
        "requirements.txt": _parse_requirements,
        "requirements-dev.txt": _parse_requirements,
        "requirements-prod.txt": _parse_requirements,
        "pyproject.toml": _parse_pyproject,
        "package.json": _parse_package_json,
        "pom.xml": _parse_pom_xml,
        "build.gradle": _parse_gradle,
    }

    for path in _walk(root):
        parser = parsers.get(path.name)
        if parser:
            try:
                versions.update(parser(path))
            except Exception:
                pass

    return versions


def annotate_graph(graph, root: Path) -> None:
    """Attach version strings to import nodes; logs unresolved imports."""
    versions = resolve_versions(root)
    resolved = unresolved = 0

    for node in graph.nodes:
        if node.kind != "import":
            continue
        # Normalize: numpy.array → numpy, @types/react → types_react
        raw = node.label.split(".")[0]
        candidates = [
            raw.lower(),
            raw.lower().replace("-", "_"),
            raw.lower().replace("_", "-"),
            raw,
        ]
        ver = next((versions[c] for c in candidates if c in versions), "")
        if ver:
            node.version = ver
            resolved += 1
        else:
            unresolved += 1

    print(f"  버전 해석: {resolved} resolved / {unresolved} unresolved")
