#!/usr/bin/env python3
"""Regenerates extera-plugins.json from the files in plugins/.

Официальная механика: https://plugins.exteragram.app/docs/plugin-repositories
Требуется Python 3.8+. Сгенерированный индекс соответствует схеме 1.

Запуск:
    python build_index.py
"""

import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLUGINS_DIR = ROOT / "plugins"
INDEX = ROOT / "extera-plugins.json"

REPOSITORY = {
    "schema": 1,
    "name": "Statik",
    "author": "ZyzaNext",
}

FIELDS = (
    "id", "name", "description", "author", "version", "icon",
    "app_version", "sdk_version", "requirements", "category",
)


def read_plugin_file(path: Path) -> dict:
    meta = {}
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id.startswith("__") and target.id.endswith("__"):
            key = target.id[2:-2]
            if key in FIELDS:
                meta[key] = ast.literal_eval(node.value)
    return meta


def main() -> None:
    previous = {}
    if INDEX.exists():
        previous = {p["id"]: p for p in json.loads(INDEX.read_text(encoding="utf-8")).get("plugins", [])}

    plugins = []
    for path in sorted(PLUGINS_DIR.rglob("*")):
        if not path.is_file() or path.suffix != ".plugin":
            continue
        meta = read_plugin_file(path)
        missing = [k for k in ("id", "name", "version") if not meta.get(k)]
        if missing:
            raise SystemExit(f"{path}: missing {', '.join(missing)}")
        if isinstance(meta.get("requirements"), list):
            meta["requirements"] = ", ".join(meta["requirements"])

        data = path.read_bytes()
        entry = {
            **meta,
            "file": path.relative_to(path.parents[2]).as_posix(),
            "sha256": hashlib.sha256(data).hexdigest(),
            "size": len(data),
        }
        old = previous.get(meta["id"], {})
        if old.get("sha256") == entry["sha256"] and old.get("updated_at"):
            entry["updated_at"] = old["updated_at"]
        else:
            entry["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        plugins.append(entry)

    ids = [p["id"] for p in plugins]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise SystemExit(f"duplicate plugin ids: {', '.join(duplicates)}")

    index = {**REPOSITORY, "plugins": plugins}
    INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{INDEX.name}: {len(plugins)} plugins")


if __name__ == "__main__":
    main()