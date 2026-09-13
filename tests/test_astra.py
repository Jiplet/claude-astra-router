from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "astra.py"
SPEC = importlib.util.spec_from_file_location("astra", SCRIPT)
assert SPEC and SPEC.loader
astra = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(astra)


class AstraRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.project = self.root / "project with spaces"
        self.project.mkdir()
        self.brief = self.root / "brief with spaces.md"
        self.prompt = "Review `literal` and $(never-run); quote: 'ok'.\n"
        self.brief.write_text(self.prompt, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def successful_process(argv, **kwargs):
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text("usable answer\n", encoding="utf-8")
        stdout = json.dumps({"type": "thread.started", "thread_id": "session-123"}) + "\n"
        stdout += json.dumps({"type": "turn.completed"}) + "\n"
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def run_once(self, run_dir=None):
        target = run_dir or self.root / "new run"
        with mock.patch.object(astra.subprocess, "run", side_effect=self.successful_process) as process:
            code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(target)])
        return code, target, process

    def test_run_uses_stdin_list_argv_spaces_and_fixed_defaults(self):
        code, run_dir, process = self.run_once()
        self.assertEqual(code, 0)
        call = process.call_args
        argv = call.args[0]
        self.assertEqual(argv[:7], ["codex", "exec", "--model", "gpt-6-astra", "--sandbox", "read-only", "--json"])
        self.assertEqual(argv[-1], "-")
        self.assertEqual(call.kwargs["input"], self.prompt)
        self.assertEqual(call.kwargs["cwd"], str(self.project.resolve()))
        self.assertNotIn("shell", call.kwargs)
        self.assertEqual(run_dir.stat().st_mode & 0o777, 0o700)
        self.assertEqual((run_dir / "brief.md").read_text(encoding="utf-8"), self.prompt)
        metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["files"]["brief"], str((run_dir / "brief.md").resolve()))

    def test_run_refuses_existing_directory(self):
        existing = self.root / "existing"
        existing.mkdir()
        with mock.patch.object(astra.subprocess, "run") as process:
            code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(existing)])
        self.assertEqual(code, 1)
        process.assert_not_called()

    def test_run_fails_without_session_id(self):
        def no_session(argv, **kwargs):
            Path(argv[argv.index("--output-last-message") + 1]).write_text("answer", encoding="utf-8")
            return subprocess.CompletedProcess(argv, 0, json.dumps({"type": "turn.completed"}), "")
        run_dir = self.root / "no session"
        with mock.patch.object(astra.subprocess, "run", side_effect=no_session):
            code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(run_dir)])
        self.assertEqual(code, 1)
        self.assertFalse((run_dir / "result.md").exists())
        self.assertTrue((run_dir / "failed-result.md").exists())
        self.assertFalse(json.loads((run_dir / "metadata.json").read_text())["success"])

    def test_run_records_failure_when_codex_cannot_start(self):
        run_dir = self.root / "missing executable"
        with mock.patch.object(astra.subprocess, "run", side_effect=FileNotFoundError("codex")):
            code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(run_dir)])
        self.assertEqual(code, 1)
        metadata = json.loads((run_dir / "metadata.json").read_text())
        self.assertFalse(metadata["success"])
        self.assertEqual(metadata["errors"], ["Codex could not be started"])

    def test_run_fails_on_nonzero_missing_result_and_turn_failed(self):
        cases = [
            subprocess.CompletedProcess([], 2, "", "problem"),
            subprocess.CompletedProcess([], 0, json.dumps({"type": "thread.started", "thread_id": "s"}), ""),
            subprocess.CompletedProcess([], 0, json.dumps({"type": "thread.started", "thread_id": "s"}) + "\n" + json.dumps({"type": "turn.failed"}), ""),
        ]
        for index, completed in enumerate(cases):
            with self.subTest(index=index):
                target = self.root / f"failed-{index}"
                def response(argv, **kwargs):
                    if index == 2:
                        Path(argv[argv.index("--output-last-message") + 1]).write_text("stale", encoding="utf-8")
                    return completed
                with mock.patch.object(astra.subprocess, "run", side_effect=response):
                    code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(target)])
                self.assertEqual(code, 1)
                self.assertFalse((target / "result.md").exists())
                metadata = json.loads((target / "metadata.json").read_text())
                self.assertIsNone(metadata["files"]["result"])

    def test_run_requires_terminal_completion_and_rejects_error_event(self):
        for label, event_lines in (
            ("incomplete", [{"type": "thread.started", "thread_id": "s"}]),
            ("error", [
                {"type": "thread.started", "thread_id": "s"},
                {"type": "error", "message": "failed"},
                {"type": "turn.completed"},
            ]),
        ):
            with self.subTest(label=label):
                target = self.root / label
                def response(argv, **kwargs):
                    Path(argv[argv.index("--output-last-message") + 1]).write_text("not accepted", encoding="utf-8")
                    stdout = "\n".join(json.dumps(event) for event in event_lines)
                    return subprocess.CompletedProcess(argv, 0, stdout, "")
                with mock.patch.object(astra.subprocess, "run", side_effect=response):
                    code = astra.main(["run", "--project", str(self.project), "--brief", str(self.brief), "--run-dir", str(target)])
                self.assertEqual(code, 1)
                self.assertFalse((target / "result.md").exists())
                self.assertIsNone(json.loads((target / "metadata.json").read_text())["files"]["result"])

    def test_revise_reuses_exact_session_model_sandbox_and_cwd(self):
        run_dir = self.root / "workspace run"
        with mock.patch.object(astra.subprocess, "run", side_effect=self.successful_process):
            code = astra.main([
                "run", "--project", str(self.project), "--brief", str(self.brief),
                "--run-dir", str(run_dir), "--sandbox", "workspace-write",
            ])
        self.assertEqual(code, 0)
        with mock.patch.object(astra.subprocess, "run", side_effect=self.successful_process) as process:
            code = astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)])
        self.assertEqual(code, 0)
        argv = process.call_args.args[0]
        self.assertEqual(argv[:7], ["codex", "exec", "--model", "gpt-6-astra", "--sandbox", "workspace-write", "--json"])
        self.assertEqual(argv[-3:], ["resume", "session-123", "-"])
        self.assertNotIn("--last", argv)
        self.assertEqual(process.call_args.kwargs["cwd"], str(self.project.resolve()))
        revision = run_dir / "revision-001"
        self.assertTrue((revision / "metadata.json").is_file())
        self.assertEqual((revision / "brief.md").read_text(encoding="utf-8"), self.prompt)
        self.assertEqual(json.loads((revision / "metadata.json").read_text())["session_id"], "session-123")

    def test_revise_rejects_mismatched_reported_session(self):
        code, run_dir, _ = self.run_once()
        self.assertEqual(code, 0)
        def mismatch(argv, **kwargs):
            Path(argv[argv.index("--output-last-message") + 1]).write_text("not accepted", encoding="utf-8")
            stdout = json.dumps({"type": "thread.started", "thread_id": "different"}) + "\n"
            stdout += json.dumps({"type": "turn.completed"}) + "\n"
            return subprocess.CompletedProcess(argv, 0, stdout, "")
        with mock.patch.object(astra.subprocess, "run", side_effect=mismatch):
            code = astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)])
        self.assertEqual(code, 1)
        metadata = json.loads((run_dir / "revision-001" / "metadata.json").read_text())
        self.assertEqual(metadata["session_id"], "session-123")
        self.assertIsNone(metadata["files"]["result"])

    def test_revise_fails_closed_for_missing_session_and_lock(self):
        run_dir = self.root / "bad run"
        run_dir.mkdir()
        (run_dir / "metadata.json").write_text(json.dumps({"model": astra.MODEL}), encoding="utf-8")
        self.assertEqual(astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)]), 1)

        metadata = {"model": astra.MODEL, "sandbox": "read-only", "project": str(self.project), "session_id": "exact", "success": True}
        (run_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
        (run_dir / ".revise.lock").write_text("", encoding="utf-8")
        with mock.patch.object(astra.subprocess, "run") as process:
            self.assertEqual(astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)]), 1)
        process.assert_not_called()

    def test_revision_limit_is_two(self):
        code, run_dir, _ = self.run_once()
        self.assertEqual(code, 0)
        for _ in range(2):
            with mock.patch.object(astra.subprocess, "run", side_effect=self.successful_process):
                self.assertEqual(astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)]), 0)
        with mock.patch.object(astra.subprocess, "run") as process:
            self.assertEqual(astra.main(["revise", "--run-dir", str(run_dir), "--brief", str(self.brief)]), 1)
        process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
