import unittest

from pathlib import Path

from scripts.run_clean_clone_layer_a import (
    clone_commands,
    layer_a_commands,
    local_submodule_copy_commands,
    missing_object_ids,
    output_label,
    sanitized_environment,
)


class CleanCloneLayerATests(unittest.TestCase):
    def test_missing_object_parser_fails_closed_on_promisor_markers(self):
        self.assertEqual(missing_object_ids("a path\nb other\n"), [])
        self.assertEqual(
            missing_object_ids("?0123456789012345678901234567890123456789\n"),
            ["0123456789012345678901234567890123456789"],
        )

    def test_output_label_supports_external_audit_path(self):
        root = Path("/repository")
        self.assertEqual(output_label(root / "audit.json", root), "audit.json")
        external = Path("/tmp/audit.json")
        self.assertEqual(output_label(external, root), str(external.resolve()))

    def test_sanitized_environment_contains_no_secret_or_provider_variables(self):
        environment = sanitized_environment("/tmp/llm4or-clean-home")
        self.assertEqual(
            set(environment),
            {
                "GIT_CONFIG_NOSYSTEM",
                "GIT_TERMINAL_PROMPT",
                "HOME",
                "LANG",
                "LC_ALL",
                "PATH",
                "PYTHONDONTWRITEBYTECODE",
                "PYTHONHASHSEED",
            },
        )
        for key in environment:
            self.assertNotIn("KEY", key)
            self.assertNotIn("TOKEN", key)
            self.assertNotIn("SECRET", key)

    def test_layer_a_commands_have_no_network_provider_or_solver_entrypoint(self):
        commands = layer_a_commands()
        self.assertEqual(len(commands), 5)
        joined = "\n".join(" ".join(command) for command in commands)
        self.assertIn("tests.test_release_evidence_reconstruction", joined)
        self.assertIn("tests.test_atomic_publisher", joined)
        self.assertIn("tests.test_reconstruction_publishers", joined)
        self.assertIn("tests.test_reviewer_claim_table", joined)
        self.assertIn("reconstruct_release_evidence.py --check", joined)
        self.assertIn("build_reviewer_claim_table.py --check", joined)
        for forbidden in ("curl", "wget", "antchat", "gurobi_cl", "pip", "openai"):
            self.assertNotIn(forbidden, joined.casefold())

    def test_clone_commands_make_local_submodule_fallback_explicit(self):
        source = Path("/source/repository")
        clone = Path("/temporary/repository")
        remote = clone_commands(source, clone, "branch", None)
        self.assertEqual(remote[0][0:3], ["git", "clone", "--no-local"])
        self.assertIn("--recurse-submodules", remote[0])
        self.assertEqual(len(remote), 1)

        local_submodule = Path("/source/repository/vendor/solver-in-the-loop")
        fallback = clone_commands(source, clone, "branch", local_submodule)
        self.assertEqual(len(fallback), 1)
        self.assertNotIn("--recurse-submodules", fallback[0])

    def test_local_submodule_snapshot_is_recloned_without_worktree_git_pointer(self):
        source = Path("/source/repository/vendor/solver-in-the-loop")
        target = Path("/temporary/repository/vendor/solver-in-the-loop")
        commands = local_submodule_copy_commands(source, target)
        self.assertEqual(
            commands[0],
            ["git", "clone", "--no-local", "--no-checkout", str(source), str(target)],
        )
        self.assertEqual(
            commands[1],
            [
                "git",
                "-C",
                str(target),
                "checkout",
                "--detach",
                "c631f9c65ad7f0ae97933c4b4c6bd6a3755e0010",
            ],
        )



if __name__ == "__main__":
    unittest.main()
