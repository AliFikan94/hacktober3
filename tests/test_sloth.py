import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sloth


class SlothTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "IMG_001.JPG").write_bytes(b"x")
        (self.d / "notes.txt").write_text("meeting notes")
        (self.d / "notes (1).txt").write_text("more")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_moves_nothing(self):
        sloth.main([str(self.d), "--no-model"])
        self.assertTrue((self.d / "IMG_001.JPG").exists())

    def test_apply_and_undo_roundtrip(self):
        sloth.main([str(self.d), "--no-model", "--apply"])
        self.assertTrue((self.d / "images" / "img-001.jpg").exists())
        self.assertFalse((self.d / "notes.txt").exists())
        sloth.main([str(self.d), "--undo"])
        self.assertEqual(sorted(p.name for p in self.d.iterdir()),
                         ["IMG_001.JPG", "notes (1).txt", "notes.txt"])

    def test_collisions_never_overwrite(self):
        moves = sloth.plan(self.d, lambda p: ("documents", "same"))
        self.assertEqual(len({m[1] for m in moves}), 3)

    def test_model_answer_used_and_bad_answer_falls_back(self):
        orig = sloth.ask_model
        try:
            sloth.ask_model = lambda *a, **k: ("documents", "team-meeting")
            sloth.main([str(self.d), "--apply", "--host", "http://x"])
            self.assertTrue((self.d / "documents" / "team-meeting.txt").exists())
        finally:
            sloth.ask_model = orig

    def test_unreachable_server_returns_none(self):
        self.assertIsNone(sloth.ask_model(self.d / "notes.txt", "http://127.0.0.1:1", "m", timeout=1))


if __name__ == "__main__":
    unittest.main()
