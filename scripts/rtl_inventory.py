#!/usr/bin/env python3
"""
Generate a raw RTL module inventory for Skybox/Vortex.

Outputs:
  - CSV index with module declarations and basic metadata
  - JSON index with the same records for machine diffing
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple


MODULE_RE = re.compile(r"^\s*module\s+([A-Za-z_][A-Za-z0-9_]*)\b")
PARAM_RE = re.compile(r"\bparameter\b(?:\s+\w+\s+)?\s*([A-Za-z_][A-Za-z0-9_]*)")
IFDEF_RE = re.compile(r"^\s*`(ifdef|ifndef|elsif|else|endif)\b(?:\s+([A-Za-z_][A-Za-z0-9_]*))?")
ENDMODULE_RE = re.compile(r"^\s*endmodule\b")


@dataclass
class ModuleDecl:
    module_name: str
    file_path: str
    language: str
    line: int
    guarded_by_ifdef: str
    parameters: List[str]
    instantiated_by: Set[str]

    def to_csv_row(self) -> Dict[str, str]:
        return {
            "module_name": self.module_name,
            "file_path": self.file_path,
            "language": self.language,
            "line": str(self.line),
            "guarded_by_ifdef": self.guarded_by_ifdef,
            "parameters": "|".join(self.parameters),
            "instantiated_by": "|".join(sorted(self.instantiated_by)),
        }

    def to_json_obj(self) -> Dict[str, object]:
        return {
            "module_name": self.module_name,
            "file_path": self.file_path,
            "language": self.language,
            "line": self.line,
            "guarded_by_ifdef": self.guarded_by_ifdef,
            "parameters": self.parameters,
            "instantiated_by": sorted(self.instantiated_by),
        }


def relpath(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def collect_rtl_files(root: Path, hw_dir: Path) -> List[Path]:
    files = []
    for ext in ("*.sv", "*.v"):
        files.extend(hw_dir.rglob(ext))
    return sorted(p for p in files if p.is_file())


def parse_modules(files: List[Path], root: Path) -> Tuple[List[ModuleDecl], Dict[str, List[ModuleDecl]]]:
    modules: List[ModuleDecl] = []
    by_name: Dict[str, List[ModuleDecl]] = {}

    for path in files:
        guard_stack: List[str] = []
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        rel = relpath(path, root)
        lang = "sv" if path.suffix == ".sv" else "v"

        for idx, line in enumerate(lines, start=1):
            ifdef_match = IFDEF_RE.match(line)
            if ifdef_match:
                kind = ifdef_match.group(1)
                token = ifdef_match.group(2) or ""
                if kind == "ifdef":
                    guard_stack.append(token)
                elif kind == "ifndef":
                    guard_stack.append(f"!{token}")
                elif kind == "elsif":
                    if guard_stack:
                        guard_stack[-1] = f"elsif:{token}"
                elif kind == "else":
                    if guard_stack:
                        guard_stack[-1] = f"else:{guard_stack[-1]}"
                elif kind == "endif":
                    if guard_stack:
                        guard_stack.pop()
                continue

            mod_match = MODULE_RE.match(line)
            if not mod_match:
                continue

            module_name = mod_match.group(1)
            params: List[str] = []
            for probe in lines[idx - 1 : min(len(lines), idx + 80)]:
                if ENDMODULE_RE.match(probe):
                    break
                params.extend(PARAM_RE.findall(probe))

            # Preserve order, remove duplicates.
            dedup_params: List[str] = []
            seen = set()
            for p in params:
                if p not in seen:
                    dedup_params.append(p)
                    seen.add(p)

            decl = ModuleDecl(
                module_name=module_name,
                file_path=rel,
                language=lang,
                line=idx,
                guarded_by_ifdef=" && ".join(guard_stack) if guard_stack else "",
                parameters=dedup_params,
                instantiated_by=set(),
            )
            modules.append(decl)
            by_name.setdefault(module_name, []).append(decl)

    return modules, by_name


def collect_instantiations(files: List[Path], root: Path, module_names: Set[str]) -> Dict[str, Set[str]]:
    inst_by: Dict[str, Set[str]] = {name: set() for name in module_names}

    # Example patterns:
    #   VX_cluster #(... ) cluster_i (
    #   VX_cluster cluster_i (
    inst_re = re.compile(
        r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:#\s*\([^;]*\))?\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("
    )

    for path in files:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        current_module = None

        for line in lines:
            mod_match = MODULE_RE.match(line)
            if mod_match:
                current_module = mod_match.group(1)
                continue

            if ENDMODULE_RE.match(line):
                current_module = None
                continue

            if current_module is None:
                continue

            stripped = line.strip()
            if not stripped or stripped.startswith("`"):
                continue
            if stripped.startswith(("if ", "for ", "while ", "case ", "assign ", "always", "initial", "wire ", "logic ", "reg ", "input ", "output ", "inout ", "localparam ", "parameter ")):
                continue

            inst_match = inst_re.match(line)
            if not inst_match:
                continue

            mod_name = inst_match.group(1)
            if mod_name in module_names:
                inst_by[mod_name].add(current_module)

    return inst_by


def write_outputs(modules: List[ModuleDecl], csv_path: Path, json_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    modules_sorted = sorted(modules, key=lambda m: (m.module_name, m.file_path, m.line))

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "module_name",
                "file_path",
                "language",
                "line",
                "guarded_by_ifdef",
                "parameters",
                "instantiated_by",
            ],
        )
        writer.writeheader()
        for mod in modules_sorted:
            writer.writerow(mod.to_csv_row())

    payload = {
        "modules_total": len(modules_sorted),
        "modules": [m.to_json_obj() for m in modules_sorted],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate RTL module inventory index")
    parser.add_argument("--repo-root", default=".", help="Repository root path")
    parser.add_argument("--hw-dir", default="hw", help="RTL root directory")
    parser.add_argument("--csv-out", default="docs/skybox_rtl_modules_index.csv", help="CSV output path")
    parser.add_argument("--json-out", default="docs/skybox_rtl_modules_index.json", help="JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    hw_dir = (root / args.hw_dir).resolve()

    files = collect_rtl_files(root, hw_dir)
    modules, by_name = parse_modules(files, root)
    instantiations = collect_instantiations(files, root, set(by_name.keys()))

    for name, decls in by_name.items():
        inst_set = instantiations.get(name, set())
        for d in decls:
            d.instantiated_by.update(inst_set)

    csv_path = (root / args.csv_out).resolve()
    json_path = (root / args.json_out).resolve()
    write_outputs(modules, csv_path, json_path)

    print(f"rtl_files={len(files)}")
    print(f"modules={len(modules)}")
    print(f"csv={csv_path}")
    print(f"json={json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
