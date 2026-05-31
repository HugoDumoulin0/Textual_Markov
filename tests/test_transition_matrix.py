import math
import sys
import unittest
from pathlib import Path

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover
    pd = None

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

if pd is not None:
    from transition_matrix import (
        build_transition_matrix,
        get_top_observed_sequences,
        normalize_filename,
        process_sequence,
        safe_folder_name,
    )


@unittest.skipIf(pd is None, "pandas is required for these tests")
class TransitionMatrixTest(unittest.TestCase):
    def test_process_sequence_stops_at_first_nan(self):
        sequence = pd.Series(["a", "b", math.nan, "c"])

        self.assertEqual(process_sequence(sequence), ["start", "a", "b", "end"])

    def test_build_transition_matrix_normalizes_counts(self):
        df = pd.DataFrame(
            [
                ["a", "b", math.nan],
                ["a", "a", math.nan],
            ]
        )

        matrix = build_transition_matrix(df)

        self.assertEqual(matrix["start"], {"a": 1.0})
        self.assertEqual(matrix["a"]["b"], 1 / 3)
        self.assertEqual(matrix["a"]["a"], 1 / 3)
        self.assertEqual(matrix["a"]["end"], 1 / 3)
        self.assertEqual(matrix["b"], {"end": 1.0})

    def test_get_top_observed_sequences_counts_from_state(self):
        df = pd.DataFrame(
            [
                ["a", "b"],
                ["a", "b"],
                ["a", "c"],
            ]
        )

        top_sequences = get_top_observed_sequences(
            df,
            start_state="a",
            length=2,
            n=2,
        )

        self.assertEqual(top_sequences[0]["sequence"], ["a", "b"])
        self.assertEqual(top_sequences[0]["count"], 2)
        self.assertAlmostEqual(top_sequences[0]["frequency"], 2 / 3)

    def test_filename_helpers(self):
        self.assertEqual(normalize_filename("/tmp/file.xml"), "file")
        self.assertEqual(safe_folder_name("annee 2000/2001"), "annee_2000_2001")


if __name__ == "__main__":
    unittest.main()
