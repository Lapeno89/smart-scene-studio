"""Build and verify a reproducible, manually installable integration ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tomllib
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT / "custom_components" / "smart_scene_studio"
DOMAIN_PATH = Path("custom_components/smart_scene_studio")
DEFAULT_OUTPUT_DIR = ROOT / "release_artifacts"
RELEASE_TAG_PREFIX = "v"
EXPECTED_FILES = {
    "__init__.py",
    "config_flow.py",
    "const.py",
    "frontend_panel.py",
    "hue_v2.py",
    "light_control.py",
    "manifest.json",
    "models.py",
    "presets.json",
    "repository.py",
    "scene.py",
    "scene_bundle.py",
    "services.yaml",
    "strings.json",
    "websocket_api.py",
    "brand/icon.png",
    "frontend/dist/smart-scene-studio.js",
    "translations/en.json",
}
FORBIDDEN_PATH_PARTS = {".git", ".venv", "node_modules", "tests", "__pycache__"}
FORBIDDEN_SUFFIXES = {".db", ".env", ".key", ".log", ".pem", ".pyc", ".p12", ".pfx", ".tmp"}
FORBIDDEN_NAMES = {".env", "credentials.json", "secrets.json", "secrets.yaml"}
VERSION_PATTERN = re.compile(r'^PANEL_ASSET_VERSION\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path.relative_to(ROOT)}")
    return data


def _source_commit() -> str:
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        raise ValueError("Commit tracked release-candidate changes before packaging")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Could not determine the exact source Git commit")
    return commit


def _collect_files() -> list[tuple[str, Path]]:
    files: list[tuple[str, Path]] = []
    for path in sorted(INTEGRATION.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(INTEGRATION)
        if any(part in FORBIDDEN_PATH_PARTS for part in relative.parts):
            continue
        if path.name.lower() in FORBIDDEN_NAMES:
            raise ValueError(f"Refusing to package credentials or secret data: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise ValueError(f"Refusing to package temporary or sensitive file: {relative}")
        if path.is_symlink():
            raise ValueError(f"Refusing to package symlink: {relative}")
        files.append((str(DOMAIN_PATH / relative).replace("\\", "/"), path))
    included = {name.removeprefix(f"{DOMAIN_PATH.as_posix()}/") for name, _ in files}
    missing = sorted(EXPECTED_FILES - included)
    if missing:
        raise ValueError(f"Required integration files are missing: {', '.join(missing)}")
    unexpected = sorted(included - EXPECTED_FILES)
    if unexpected:
        raise ValueError(
            "Unexpected integration files require explicit packaging review: "
            + ", ".join(unexpected)
        )
    if not (ROOT / "LICENSE").is_file():
        raise ValueError("Root LICENSE file is required in the release archive")
    return files


def _release_metadata(version: str, commit: str) -> bytes:
    metadata = {
        "candidate_tag": f"{RELEASE_TAG_PREFIX}{version}",
        "manifest_version": version,
        "name": "Smart Scene Studio",
        "source_commit": commit,
        "status": "release candidate; not published",
    }
    return (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _verify_archive(archive_path: Path, version: str, commit: str) -> int:
    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise ValueError(f"Corrupt ZIP member: {bad_member}")
        names = set(archive.namelist())
        required = {f"{DOMAIN_PATH.as_posix()}/{name}" for name in EXPECTED_FILES}
        required.update({"LICENSE", "RELEASE_CANDIDATE.json"})
        missing = sorted(required - names)
        if missing:
            raise ValueError(f"ZIP is missing required files: {', '.join(missing)}")
        for name in names:
            parts = Path(name).parts
            if any(part in FORBIDDEN_PATH_PARTS for part in parts):
                raise ValueError(f"Forbidden path in ZIP: {name}")
            if Path(name).suffix.lower() in FORBIDDEN_SUFFIXES:
                raise ValueError(f"Forbidden file in ZIP: {name}")
        manifest = json.loads(archive.read(f"{DOMAIN_PATH.as_posix()}/manifest.json"))
        presets = json.loads(archive.read(f"{DOMAIN_PATH.as_posix()}/presets.json"))
        metadata = json.loads(archive.read("RELEASE_CANDIDATE.json"))
        if manifest.get("version") != version or metadata.get("manifest_version") != version:
            raise ValueError("Manifest, release metadata, and expected versions do not match")
        if metadata.get("candidate_tag", "").removeprefix("v") != version:
            raise ValueError("Candidate tag and manifest version do not match")
        if metadata.get("source_commit") != commit:
            raise ValueError("ZIP provenance commit does not match the source revision")
        if not isinstance(presets, list) or len(presets) != 11:
            raise ValueError("Release ZIP must contain exactly the 11 original preset scenes")
        return len(names)


def build_release_zip(output: Path | None = None) -> tuple[Path, str, int, str]:
    manifest = _read_json(INTEGRATION / "manifest.json")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    package = _read_json(ROOT / "frontend" / "package.json")
    version = str(manifest.get("version", ""))
    if not version or project.get("version") != version or package.get("version") != version:
        raise ValueError("manifest.json, pyproject.toml, and frontend package versions must match")
    panel_source = (INTEGRATION / "frontend_panel.py").read_text(encoding="utf-8")
    match = VERSION_PATTERN.search(panel_source)
    if match is None or match.group(1) != version:
        raise ValueError("Panel asset cache version must match the release version")
    core_version = str(project["dependencies"][0]).split("==", maxsplit=1)[-1]
    hacs = _read_json(ROOT / "hacs.json")
    if hacs.get("homeassistant") != core_version:
        raise ValueError(
            "hacs.json minimum Home Assistant version must match the pinned Core version"
        )

    commit = _source_commit()
    files = _collect_files()
    archive_path = output or DEFAULT_OUTPUT_DIR / f"Smart-Scene-Studio-v{version}.zip"
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, path in files:
            archive.writestr(
                _zip_info(name),
                path.read_bytes(),
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
        archive.writestr(_zip_info("LICENSE"), (ROOT / "LICENSE").read_bytes(), compresslevel=9)
        archive.writestr(
            _zip_info("RELEASE_CANDIDATE.json"),
            _release_metadata(version, commit),
            compresslevel=9,
        )

    entry_count = _verify_archive(archive_path, version, commit)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    sidecar = archive_path.with_suffix(archive_path.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")
    return archive_path, commit, entry_count, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, help="ZIP output path (defaults to release_artifacts/)"
    )
    args = parser.parse_args()
    archive, commit, entry_count, digest = build_release_zip(args.output)
    print(f"Archive: {archive}")
    print(f"Source commit: {commit}")
    print(f"ZIP entries: {entry_count}")
    print(f"SHA-256: {digest}")
    print("Verification: passed (required files, versions, provenance, and excluded-file checks)")


if __name__ == "__main__":
    main()
