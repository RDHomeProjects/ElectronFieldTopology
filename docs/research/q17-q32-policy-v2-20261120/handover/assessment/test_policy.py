"""Read-only regression tests. No optimizer or physical-time solver is invoked."""
import unittest
from unittest.mock import patch
import ast
import json
from pathlib import Path
import audit

ROOT = Path(__file__).resolve().parent


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.objects, cls.verification = audit.evidence()
        cls.plan = cls.objects["record.json"]["plan"]
        cls.old = audit.module("test_old", "original/fits.py")
        cls.new = audit.module("test_new", "corrected/policy_v2.py")

    def run_decision(self, rows, count, epoch, remaining=100):
        def no_models(*_):
            return {"accepted": [], "rejected": [], "reason": "test leaves model selection unexercised"}
        with patch.object(self.new, "models", side_effect=no_models):
            return self.new.decide(rows, self.plan, remaining, count, plateau_epoch=epoch)

    @staticmethod
    def rows(iterations, force=.01, acceleration=.1):
        return [{"iteration": i, "relative_force_l2": force, "acceleration_max": acceleration, "energy": 20 - i * 1e-5} for i in iterations]

    def test_real_q22_reset_stop_changes(self):
        ds = self.objects["broad/q22-cable-source-family/optimizer/decisions.json"]
        hs = self.objects["broad/q22-cable-source-family/optimizer/history.json"]
        self.assertEqual([x["plateau_count"] for x in ds[-3:]], [1, 2, 3])
        with audit.saved_models(self.new, ds[-1]):
            new = self.new.decide(hs, self.plan, 100, 2, plateau_epoch=0)
        self.assertEqual(new["distinct_epoch_observations"], 1)
        self.assertIsNone(new["recent_joint_progress"])
        self.assertEqual(new["plateau_count"], 0)
        self.assertEqual(new["action"], "continue")
        self.assertLessEqual(new["steps"], 100)

    def test_missing_epoch_is_explicit_error(self):
        with self.assertRaises(TypeError):
            self.new.decide(self.rows(range(200, 208)), self.plan, 100, 2)

    def test_epoch_change_resets_old_counter_even_after_full_window(self):
        d = self.run_decision(self.rows(range(200, 221)), 2, 0)
        self.assertTrue(d["progress_evidence_sufficient"])
        self.assertEqual(d["plateau_count"], 1)
        self.assertEqual(d["action"], "continue")

    def test_short_window_cannot_vote_for_stagnation(self):
        d = self.run_decision(self.rows(range(200, 207)), 2, 200)
        self.assertEqual(d["plateau_count"], 0)
        self.assertFalse(d["progress_evidence_sufficient"])
        self.assertEqual(d["action"], "continue")

    def test_distinct_observations_required(self):
        d = self.run_decision(self.rows([210] * 10), 2, 200)
        self.assertEqual(d["distinct_epoch_observations"], 1)
        self.assertEqual(d["plateau_count"], 0)

    def test_three_supported_decisions_still_stop(self):
        d = self.run_decision(self.rows(range(200, 221)), 2, 200)
        self.assertEqual(d["plateau_count"], 3)
        self.assertEqual(d["action"], "stop")

    def test_exploratory_floor_preserved(self):
        d = self.run_decision(self.rows(range(130, 141)), 2, 0)
        self.assertEqual(d["plateau_count"], 0)
        self.assertEqual(d["action"], "continue")

    def test_attempt_budget_exhaustion_preserved(self):
        d = self.run_decision(self.rows(range(290, 301)), 0, 200, remaining=0)
        self.assertEqual(d["action"], "stop")
        self.assertEqual(d["steps"], 0)

    def test_small_remaining_budget_not_exceeded(self):
        d = self.run_decision(self.rows(range(200, 204)), 0, 200, remaining=3)
        self.assertEqual(d["action"], "continue")
        self.assertLessEqual(d["steps"], 3)

    def test_fitting_implementations_unchanged(self):
        original = ast.parse((ROOT / "original/fits.py").read_text())
        corrected = ast.parse((ROOT / "corrected/policy_v2.py").read_text())
        for name in ("fit_model", "predict", "models"):
            a = next(x for x in original.body if isinstance(x, ast.FunctionDef) and x.name == name)
            b = next(x for x in corrected.body if isinstance(x, ast.FunctionDef) and x.name == name)
            self.assertEqual(ast.dump(a), ast.dump(b))

    def test_all_saved_decisions_and_affected_set(self):
        replay = audit.replay(self.objects)
        self.assertEqual(replay["original_decisions_reproduced"], 881)
        self.assertEqual(replay["branches_replayed"], 29)
        changed = {x["seed"] for x in replay["results"] if x["terminal"]["corrected_action"] != "stop"}
        self.assertEqual(changed, {"q18-axial-6-3", "q21-axial-7-3", "q22-cable-source-family", "q24-torus72-5-2", "q30-axial-6-5", "q30-torus72-8-2"})
        self.assertEqual(replay["affected_unused_attempts"], 538)

    def test_five_representation_cases_have_no_planner_stops(self):
        rows = [r for r in self.objects["record.json"]["broad"] if r["status"] == "representation_unresolved"]
        self.assertEqual(len(rows), 5)
        self.assertTrue(all("broad/" + r["seed"]["id"] + "/optimizer/decisions.json" not in self.objects for r in rows))


if __name__ == "__main__":
    unittest.main()
