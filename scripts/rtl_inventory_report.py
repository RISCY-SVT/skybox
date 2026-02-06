#!/usr/bin/env python3
"""Generate subsystem-oriented RTL inventory reports from Stage09 module index."""

from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List


SUBSYSTEM_ORDER = [
    "top",
    "core",
    "mem",
    "cache",
    "raster",
    "tex",
    "om",
    "fpu",
    "interfaces",
    "afu",
    "libs",
    "other",
]

TOP_CANDIDATE_RE = re.compile(
    r"^(Vortex(_axi)?|VX_(cluster|socket|core|core_top|graphics|.*_top|.*_unit|.*_wrap|.*_afu))$"
)


@dataclass
class ModuleRecord:
    module_name: str
    file_path: str
    line: int
    guarded_by_ifdef: str
    parameters: List[str]
    instantiated_by: List[str]
    subsystem: str


def run_cmd(args: List[str], cwd: Path) -> str:
    return subprocess.check_output(args, cwd=str(cwd), text=True).strip()


def classify_subsystem(path: str) -> str:
    if path.startswith("hw/rtl/core/"):
        return "core"
    if path.startswith("hw/rtl/mem/"):
        return "mem"
    if path.startswith("hw/rtl/cache/"):
        return "cache"
    if path.startswith("hw/rtl/raster/"):
        return "raster"
    if path.startswith("hw/rtl/tex/"):
        return "tex"
    if path.startswith("hw/rtl/om/"):
        return "om"
    if path.startswith("hw/rtl/fpu/"):
        return "fpu"
    if path.startswith("hw/rtl/interfaces/"):
        return "interfaces"
    if path.startswith("hw/rtl/afu/"):
        return "afu"
    if path.startswith("hw/rtl/libs/"):
        return "libs"
    if path.startswith("hw/rtl/"):
        return "top"
    return "other"


def load_records(index_json: Path) -> List[ModuleRecord]:
    payload = json.loads(index_json.read_text(encoding="utf-8"))
    records: List[ModuleRecord] = []
    for mod in payload.get("modules", []):
        file_path = str(mod.get("file_path", ""))
        rec = ModuleRecord(
            module_name=str(mod.get("module_name", "")),
            file_path=file_path,
            line=int(mod.get("line", 0)),
            guarded_by_ifdef=str(mod.get("guarded_by_ifdef", "")),
            parameters=list(mod.get("parameters", [])),
            instantiated_by=list(mod.get("instantiated_by", [])),
            subsystem=classify_subsystem(file_path),
        )
        records.append(rec)
    return sorted(records, key=lambda r: (r.subsystem, r.module_name, r.file_path, r.line))


def is_top_candidate(rec: ModuleRecord) -> bool:
    return TOP_CANDIDATE_RE.match(rec.module_name) is not None


def escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def format_list(values: Iterable[str], default: str = "-") -> str:
    items = [v for v in values if v]
    return ", ".join(items) if items else default


def write_csv(records: List[ModuleRecord], csv_out: Path) -> None:
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with csv_out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "subsystem",
                "module_name",
                "file_path",
                "line",
                "guarded_by_ifdef",
                "parameters",
                "instantiated_by",
                "top_candidate",
            ],
        )
        writer.writeheader()
        for rec in records:
            writer.writerow(
                {
                    "subsystem": rec.subsystem,
                    "module_name": rec.module_name,
                    "file_path": rec.file_path,
                    "line": rec.line,
                    "guarded_by_ifdef": rec.guarded_by_ifdef,
                    "parameters": "|".join(rec.parameters),
                    "instantiated_by": "|".join(rec.instantiated_by),
                    "top_candidate": "1" if is_top_candidate(rec) else "0",
                }
            )


def write_md(records: List[ModuleRecord], md_out: Path, repo_root: Path) -> None:
    md_out.parent.mkdir(parents=True, exist_ok=True)
    sha = run_cmd(["git", "rev-parse", "HEAD"], repo_root)
    submods = run_cmd(["git", "submodule", "status", "--recursive"], repo_root)

    groups: Dict[str, List[ModuleRecord]] = {k: [] for k in SUBSYSTEM_ORDER}
    for rec in records:
        groups.setdefault(rec.subsystem, []).append(rec)

    lines: List[str] = []
    lines.append("# Skybox RTL modules grouped by subsystem")
    lines.append("")
    lines.append(f"- Skybox git SHA: `{sha}`")
    lines.append("- Source index: `docs/skybox_rtl_modules_index.json`")
    lines.append(f"- Total module declarations: `{len(records)}`")
    lines.append("- Submodule snapshot:")
    for raw in submods.splitlines():
        lines.append(f"  - `{raw.strip()}`")
    lines.append("")

    lines.append("## Subsystem summary")
    lines.append("")
    lines.append("| Subsystem | Modules | Top-candidate modules (heuristic) |")
    lines.append("|---|---:|---|")
    for subsystem in SUBSYSTEM_ORDER:
        mods = groups.get(subsystem, [])
        if not mods:
            continue
        top_list = [m.module_name for m in mods if is_top_candidate(m)]
        top_preview = ", ".join(top_list[:8]) if top_list else "-"
        if len(top_list) > 8:
            top_preview += f" (+{len(top_list) - 8})"
        lines.append(f"| `{subsystem}` | {len(mods)} | {escape_md(top_preview)} |")
    lines.append("")

    for subsystem in SUBSYSTEM_ORDER:
        mods = groups.get(subsystem, [])
        if not mods:
            continue
        lines.append(f"## {subsystem} ({len(mods)})")
        lines.append("")
        lines.append("| Module | File | Guard | Parameters | Instantiated by |")
        lines.append("|---|---|---|---|---|")
        for rec in mods:
            params = format_list(rec.parameters)
            inst_by = format_list(rec.instantiated_by)
            lines.append(
                "| "
                + f"`{escape_md(rec.module_name)}` | `{escape_md(rec.file_path)}:{rec.line}` | "
                + f"`{escape_md(rec.guarded_by_ifdef or '-')}` | `{escape_md(params)}` | `{escape_md(inst_by)}` |"
            )
        lines.append("")

    md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate subsystem report from RTL module index")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument(
        "--index-json",
        default="docs/skybox_rtl_modules_index.json",
        help="Input module index JSON generated by scripts/rtl_inventory.py",
    )
    parser.add_argument(
        "--md-out",
        default="docs/skybox_rtl_modules_by_subsystem.md",
        help="Markdown report output",
    )
    parser.add_argument(
        "--csv-out",
        default="docs/skybox_rtl_modules_by_subsystem.csv",
        help="CSV output",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    index_json = (repo_root / args.index_json).resolve()
    md_out = (repo_root / args.md_out).resolve()
    csv_out = (repo_root / args.csv_out).resolve()

    records = load_records(index_json)
    write_csv(records, csv_out)
    write_md(records, md_out, repo_root)

    print(f"records={len(records)}")
    print(f"csv={csv_out}")
    print(f"md={md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
