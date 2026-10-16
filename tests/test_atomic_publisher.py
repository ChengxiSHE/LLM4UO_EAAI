import os
import multiprocessing
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from llm4or.atomic_publisher import (
    PublicationBoundaryError,
    PublicationConflict,
    _read_regular,
    publish_bundle,
    publish_bytes,
)


def _publish_worker(root, path, payload, start, results):
    start.wait(10)
    try:
        value = publish_bytes(Path(root), path, payload)
        results.put(("ok", value.created, value.identical))
    except Exception as exc:  # pragma: no cover - asserted in parent process
        results.put((type(exc).__name__, str(exc)))


class AtomicPublisherBoundaryTests(unittest.TestCase):
    def test_first_publish_and_identical_replay_are_complete_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = publish_bytes(root, "results/value.json", b'{"value":1}\n')
            replay = publish_bytes(root, "results/value.json", b'{"value":1}\n')

            self.assertEqual((root / "results/value.json").read_bytes(), b'{"value":1}\n')
            self.assertEqual(first.created, ("results/value.json",))
            self.assertEqual(first.identical, ())
            self.assertEqual(replay.created, ())
            self.assertEqual(replay.identical, ("results/value.json",))
            self.assertFalse((root / ".llm4or-publication-journal").exists())

    def test_different_existing_bytes_fail_without_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "results/value.json"
            target.parent.mkdir()
            target.write_bytes(b"first")

            with self.assertRaises(PublicationConflict):
                publish_bytes(root, target, b"second")

            self.assertEqual(target.read_bytes(), b"first")

    def test_rejects_absolute_and_parent_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside.json"
            for path in (outside, "../outside.json", "safe/../inside.json"):
                with self.subTest(path=path):
                    with self.assertRaises(PublicationBoundaryError):
                        publish_bytes(root, path, b"value")
            self.assertFalse(outside.exists())
            self.assertFalse((root / "inside.json").exists())

    def test_rejects_symlinked_parent_component(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root / "outside"
            outside.mkdir()
            (root / "linked").symlink_to(outside, target_is_directory=True)

            with self.assertRaises(PublicationBoundaryError):
                publish_bytes(root, "linked/value.json", b"value")

            self.assertFalse((outside / "value.json").exists())

    def test_rejects_symlink_terminal_without_following_it(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actual = root / "actual.json"
            actual.write_bytes(b"original")
            terminal = root / "terminal.json"
            terminal.symlink_to(actual)

            with self.assertRaises(PublicationBoundaryError):
                publish_bytes(root, terminal, b"replacement")

            self.assertEqual(actual.read_bytes(), b"original")

    def test_rejects_non_regular_terminal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            terminal = root / "terminal.json"
            terminal.mkdir()

            with self.assertRaises(PublicationBoundaryError):
                publish_bytes(root, terminal, b"replacement")

    def test_rechecks_terminal_type_after_open_to_close_stat_open_race(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "value").write_bytes(b"regular-at-stat")
            parent = os.open(root, os.O_RDONLY)
            real_open = os.open

            def swapped_open(path, flags, *args, **kwargs):
                if path == "value":
                    return real_open(root, os.O_RDONLY)
                return real_open(path, flags, *args, **kwargs)

            try:
                with mock.patch(
                    "llm4or.atomic_publisher.os.open", side_effect=swapped_open
                ):
                    with self.assertRaises(PublicationBoundaryError):
                        _read_regular(parent, "value")
            finally:
                os.close(parent)

    def test_missing_after_stat_is_treated_as_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "value").write_bytes(b"present-at-stat")
            parent = os.open(root, os.O_RDONLY)
            real_open = os.open

            def removed_before_open(path, flags, *args, **kwargs):
                if path == "value":
                    raise FileNotFoundError(path)
                return real_open(path, flags, *args, **kwargs)

            try:
                with mock.patch(
                    "llm4or.atomic_publisher.os.open", side_effect=removed_before_open
                ):
                    self.assertIsNone(_read_regular(parent, "value"))
            finally:
                os.close(parent)


class AtomicPublisherTransactionTests(unittest.TestCase):
    def _race(self, payloads):
        context = multiprocessing.get_context("fork")
        with tempfile.TemporaryDirectory() as directory:
            start = context.Event()
            results = context.Queue()
            processes = [
                context.Process(
                    target=_publish_worker,
                    args=(directory, "result/value.bin", payload, start, results),
                )
                for payload in payloads
            ]
            for process in processes:
                process.start()
            start.set()
            values = [results.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            terminal = (Path(directory) / "result/value.bin").read_bytes()
            return values, terminal

    def test_concurrent_identical_writers_both_succeed(self):
        results, terminal = self._race([b"same", b"same"])
        self.assertEqual([row[0] for row in results], ["ok", "ok"])
        self.assertEqual(terminal, b"same")

    def test_concurrent_different_writers_never_replace_the_winner(self):
        results, terminal = self._race([b"first", b"second"])
        self.assertEqual(sorted(row[0] for row in results), ["PublicationConflict", "ok"])
        self.assertIn(terminal, (b"first", b"second"))

    def test_cross_directory_bundle_replays_after_first_destination_crash(self):
        class SimulatedCrash(RuntimeError):
            pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {
                "docs/report.md": b"# report\n",
                "results/report.json": b'{"status":"ok"}\n',
            }

            def crash_after_first(phase):
                if phase == "after_publish:docs/report.md":
                    raise SimulatedCrash(phase)

            with self.assertRaises(SimulatedCrash):
                publish_bundle(root, entries, _fault=crash_after_first)
            self.assertEqual((root / "docs/report.md").read_bytes(), b"# report\n")
            self.assertFalse((root / "results/report.json").exists())
            self.assertTrue((root / ".llm4or-publication-journal").is_dir())

            recovered = publish_bundle(root, entries)

            self.assertEqual(recovered.created, ("results/report.json",))
            self.assertEqual(recovered.identical, ("docs/report.md",))
            self.assertEqual(
                (root / "results/report.json").read_bytes(),
                b'{"status":"ok"}\n',
            )
            self.assertFalse((root / ".llm4or-publication-journal").exists())

    def test_cross_directory_bundle_blocks_different_recovery_payload(self):
        class SimulatedCrash(RuntimeError):
            pass

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {"a/one": b"one", "b/two": b"two"}

            def crash_after_reservation(phase):
                if phase == "reservations_durable":
                    raise SimulatedCrash(phase)

            with self.assertRaises(SimulatedCrash):
                publish_bundle(root, entries, _fault=crash_after_reservation)
            with self.assertRaises(PublicationConflict):
                publish_bundle(root, {"a/one": b"changed", "b/two": b"two"})
            self.assertFalse((root / "a/one").exists())
            self.assertFalse((root / "b/two").exists())

    def test_replay_recovers_after_journal_and_before_cleanup_interruptions(self):
        class SimulatedCrash(RuntimeError):
            pass

        for phase in ("journal_durable", "before_cleanup"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)

                def crash(selected):
                    if selected == phase:
                        raise SimulatedCrash(selected)

                with self.assertRaises(SimulatedCrash):
                    publish_bytes(root, "result/value", b"complete", _fault=crash)

                recovered = publish_bytes(root, "result/value", b"complete")

                self.assertEqual((root / "result/value").read_bytes(), b"complete")
                self.assertEqual(
                    recovered.identical,
                    ("result/value",) if phase == "before_cleanup" else (),
                )
                self.assertFalse((root / ".llm4or-publication-journal").exists())

    def test_publisher_fsyncs_regular_files_and_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            observed = []
            real_fsync = os.fsync

            def recording_fsync(descriptor):
                observed.append(stat.S_ISDIR(os.fstat(descriptor).st_mode))
                return real_fsync(descriptor)

            with mock.patch(
                "llm4or.atomic_publisher.os.fsync", side_effect=recording_fsync
            ):
                publish_bytes(Path(directory), "result/value", b"complete")

            self.assertIn(False, observed)
            self.assertIn(True, observed)


if __name__ == "__main__":
    unittest.main()
