#!/usr/bin/env python3
"""Route a bounded brief to gpt-6-astra through the Codex CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

MODEL = "gpt-6-astra"
MAX_REVISIONS = 2


class RouterError(Exception):
    pass


def _read_brief(path: str) -> tuple[Path, str]:
    brief = Path(path).expanduser().resolve()
    if not brief.is_file():
        raise RouterError("brief file does not exist")
    text = brief.read_text(encoding="utf-8")
    if not text.strip():
        raise RouterError("brief file is empty")
    return brief, text


def _event_summary(stdout: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    events: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        events.append(event)
        kind = str(event.get("type", "unknown"))
        counts[kind] = counts.get(kind, 0) + 1
    return events, counts


def _session_id(events: list[dict[str, Any]]) -> str | None:
    for event in events:
        if event.get("type") == "thread.started":
            value = event.get("thread_id") or event.get("session_id")
            if isinstance(value, str) and value.strip():
                return value
    return None


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_codex(
    *, argv: list[str], prompt: str, cwd: Path, output_dir: Path,
    base_metadata: dict[str, Any], require_session: bool,
    expected_session: str | None = None,
) -> dict[str, Any]:
    result_path = output_dir / "result.md"
    events_path = output_dir / "events.jsonl"
    stderr_path = output_dir / "stderr.log"
    metadata_path = output_dir / "metadata.json"
    brief_snapshot_path = output_dir / "brief.md"
    brief_snapshot_path.write_text(prompt, encoding="utf-8")

    try:
        completed = subprocess.run(
            argv, input=prompt, text=True, capture_output=True, cwd=str(cwd), check=False
        )
    except OSError as exc:
        events_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        _write_json(metadata_path, {
            **base_metadata,
            "success": False,
            "return_code": None,
            "session_id": base_metadata.get("session_id"),
            "counts": {"stdout_lines": 0, "parsed_events": 0, "event_types": {}},
            "files": {
                "brief": str(brief_snapshot_path), "events": str(events_path),
                "stderr": str(stderr_path), "result": None,
            },
            "errors": ["Codex could not be started"],
        })
        raise RouterError("Codex could not be started") from exc
    events_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    events, counts = _event_summary(completed.stdout)
    reported_session = _session_id(events)
    session = expected_session or reported_session
    completed_event = any(event.get("type") == "turn.completed" for event in events)
    terminal_error = any(event.get("type") in {"turn.failed", "error"} for event in events)
    usable_result = result_path.is_file() and bool(result_path.read_text(encoding="utf-8").strip())

    problems: list[str] = []
    if completed.returncode != 0:
        problems.append("Codex exited with a non-zero status")
    if terminal_error:
        problems.append("Codex reported an error event")
    if not completed_event:
        problems.append("Codex did not report turn.completed")
    if require_session and not reported_session:
        problems.append("Codex did not report a session ID")
    if expected_session and reported_session and reported_session != expected_session:
        problems.append("Codex resumed a different session ID")
    if not usable_result:
        problems.append("Codex did not produce a usable result")

    metadata = {
        **base_metadata,
        "success": not problems,
        "return_code": completed.returncode,
        "session_id": session or base_metadata.get("session_id"),
        "counts": {
            "stdout_lines": len(completed.stdout.splitlines()),
            "parsed_events": len(events),
            "event_types": counts,
        },
        "files": {
            "brief": str(brief_snapshot_path),
            "events": str(events_path),
            "stderr": str(stderr_path),
            "result": str(result_path),
        },
        "errors": problems,
    }
    if problems:
        metadata["files"]["result"] = None
        if result_path.exists():
            failed_path = output_dir / "failed-result.md"
            result_path.replace(failed_path)
            metadata["files"]["failed_result"] = str(failed_path)
    _write_json(metadata_path, metadata)
    if problems:
        raise RouterError("; ".join(problems))
    return metadata


def run(args: argparse.Namespace) -> Path:
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        raise RouterError("project directory does not exist")
    brief_path, prompt = _read_brief(args.brief)
    run_dir = Path(args.run_dir).expanduser().resolve()
    try:
        run_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise RouterError("run directory already exists") from exc
    except FileNotFoundError as exc:
        raise RouterError("run directory parent does not exist") from exc
    os.chmod(run_dir, 0o700)
    result_path = run_dir / "result.md"
    argv = [
        "codex", "exec", "--model", MODEL, "--sandbox", args.sandbox,
        "--json", "--output-last-message", str(result_path), "-",
    ]
    _run_codex(
        argv=argv,
        prompt=prompt,
        cwd=project,
        output_dir=run_dir,
        base_metadata={
            "command": "run", "model": MODEL, "sandbox": args.sandbox,
            "project": str(project), "brief": str(brief_path), "revision": 0,
        },
        require_session=True,
        expected_session=None,
    )
    return run_dir


def revise(args: argparse.Namespace) -> Path:
    run_dir = Path(args.run_dir).expanduser().resolve()
    metadata_path = run_dir / "metadata.json"
    if not run_dir.is_dir() or not metadata_path.is_file():
        raise RouterError("existing run directory is invalid")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise RouterError("run metadata is unreadable") from exc
    session = metadata.get("session_id")
    if not isinstance(session, str) or not session.strip():
        raise RouterError("run metadata has no session ID")
    if metadata.get("success") is not True:
        raise RouterError("the original run did not complete successfully")
    if metadata.get("model") != MODEL:
        raise RouterError("run metadata does not use the required model")
    sandbox = metadata.get("sandbox")
    if sandbox not in {"read-only", "workspace-write"}:
        raise RouterError("run metadata has an invalid sandbox")
    project = Path(str(metadata.get("project", ""))).resolve()
    if not project.is_dir():
        raise RouterError("recorded project directory does not exist")
    brief_path, prompt = _read_brief(args.brief)

    lock_path = run_dir / ".revise.lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RouterError("another revision is in progress") from exc
    os.close(lock_fd)
    try:
        existing = [
            p for p in run_dir.iterdir()
            if p.is_dir() and p.name.startswith("revision-") and p.name[9:].isdigit()
        ]
        if len(existing) >= MAX_REVISIONS:
            raise RouterError("revision limit reached; human review is required")
        number = len(existing) + 1
        revision_dir = run_dir / f"revision-{number:03d}"
        revision_dir.mkdir(mode=0o700, exist_ok=False)
        os.chmod(revision_dir, 0o700)
        result_path = revision_dir / "result.md"
        argv = [
            "codex", "exec", "--model", MODEL, "--sandbox", sandbox,
            "--json", "--output-last-message", str(result_path),
            "resume", session, "-",
        ]
        _run_codex(
            argv=argv,
            prompt=prompt,
            cwd=project,
            output_dir=revision_dir,
            base_metadata={
                "command": "revise", "model": MODEL, "sandbox": sandbox,
                "project": str(project), "brief": str(brief_path),
                "session_id": session, "revision": number,
            },
            require_session=False,
            expected_session=session,
        )
        return revision_dir
    finally:
        lock_path.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    start = commands.add_parser("run", help="start a new Astra review")
    start.add_argument("--project", required=True)
    start.add_argument("--brief", required=True)
    start.add_argument("--run-dir", required=True)
    start.add_argument("--sandbox", choices=("read-only", "workspace-write"), default="read-only")
    start.set_defaults(handler=run)
    revision = commands.add_parser("revise", help="revise in the captured Astra session")
    revision.add_argument("--run-dir", required=True)
    revision.add_argument("--brief", required=True)
    revision.set_defaults(handler=revise)
    return cli


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        output_dir = args.handler(args)
    except RouterError as exc:
        print(f"astra router failed: {exc}", file=sys.stderr)
        return 1
    print(f"run directory: {output_dir}")
    print(f"metadata: {output_dir / 'metadata.json'}")
    print(f"result: {output_dir / 'result.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
