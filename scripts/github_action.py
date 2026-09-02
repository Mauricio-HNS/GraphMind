from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

ACTION_ROOT = Path(os.environ["GRAPHMIND_ACTION_PATH"])
WORKSPACE = Path.cwd()
BACKEND = ACTION_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.services.chart_analysis import analyze_job
from app.services.processor import process_file

SUPPORTED = {".png", ".jpg", ".jpeg", ".webp", ".pdf", ".csv", ".xlsx", ".xls", ".zip"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def read_prompt() -> str:
    prompt_file = os.getenv("GRAPHMIND_PROMPT_FILE", "").strip()
    if prompt_file:
        candidate = WORKSPACE / prompt_file
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text
    return os.getenv("GRAPHMIND_PROMPT", "Analyze the charts and identify supported findings.").strip()


def collect_files(input_dir: Path, max_files: int) -> list[Path]:
    if not input_dir.exists():
        raise SystemExit(f"GraphMind input directory does not exist: {input_dir}")
    files = [p for p in input_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED]
    return sorted(files)[:max_files]


def fallback_document(path: Path) -> dict:
    return {
        "chart": {
            "chart_id": path.stem,
            "source_file": str(path.relative_to(WORKSPACE)),
            "metadata": {
                "source_path": str(path),
                "processing_stage": "repository_ingestion",
            },
        },
        "analysis_plan": {},
        "chunks": [],
        "processing": {"status": "ingested", "supported": True},
    }


def flatten_rows(results: list[dict]) -> list[dict]:
    rows = []
    for result in results:
        chart = result.get("chart", {})
        for series in chart.get("series", []):
            for point in series.get("values", []):
                rows.append({
                    "chart_id": chart.get("chart_id", ""),
                    "source_file": chart.get("source_file", ""),
                    "series": series.get("name", ""),
                    "label": point.get("label", ""),
                    "value": point.get("value", ""),
                    "unit": series.get("unit") or point.get("unit", ""),
                })
    return rows


def markdown(analysis: dict, results: list[dict], prompt: str) -> str:
    lines = ["# GraphMind Analysis", "", f"Prompt: {prompt}", ""]
    lines += [
        f"Status: {analysis.get('status', 'unknown')}",
        f"Confidence: {analysis.get('confidence', 0):.0%}",
        f"Safe to answer: {analysis.get('safe_to_answer', False)}",
        "",
        "## Findings",
    ]
    findings = analysis.get("findings", [])
    if findings:
        for finding in findings:
            lines.append(f"- {finding}")
    else:
        lines.append("- No supported findings were produced.")
    lines += ["", "## Evidence"]
    evidence = analysis.get("evidence", [])
    if evidence:
        for item in evidence:
            lines.append(f"- {item}")
    else:
        lines.append("- No evidence references available.")
    warnings = analysis.get("warnings", [])
    if warnings:
        lines += ["", "## Warnings"]
        lines.extend(f"- {warning}" for warning in warnings)
    lines += ["", "## Sources"]
    for result in results:
        chart = result.get("chart", {})
        lines.append(f"- `{chart.get('source_file', chart.get('chart_id', 'unknown'))}`")
    return "\n".join(lines) + "\n"


def set_output(name: str, value: Path) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main() -> None:
    input_dir = WORKSPACE / os.getenv("GRAPHMIND_INPUT", "charts")
    output_dir = WORKSPACE / os.getenv("GRAPHMIND_OUTPUT", "results")
    max_files = max(1, int(os.getenv("GRAPHMIND_MAX_FILES", "50")))
    prompt = read_prompt()
    files = collect_files(input_dir, max_files)
    if not files:
        raise SystemExit(f"No supported chart files found in {input_dir}")

    results = []
    for path in files:
        if path.suffix.lower() in IMAGE_EXTENSIONS:
            results.append(process_file(path, prompt))
        else:
            results.append(fallback_document(path))

    analysis = analyze_job(results, prompt)
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "analysis.json"
    md_path = output_dir / "analysis.md"
    csv_path = output_dir / "extracted-data.csv"

    json_path.write_text(json.dumps({"prompt": prompt, "analysis": analysis, "charts": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown(analysis, results, prompt), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["chart_id", "source_file", "series", "label", "value", "unit"])
        writer.writeheader()
        writer.writerows(flatten_rows(results))

    set_output("analysis", md_path)
    set_output("json", json_path)
    set_output("csv", csv_path)
    print(f"GraphMind processed {len(files)} file(s). Status={analysis.get('status')} confidence={analysis.get('confidence', 0):.2f}")


if __name__ == "__main__":
    main()
