import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts" / "launch_workbench.py"


def load_launcher():
    spec = importlib.util.spec_from_file_location("atlas_launcher", LAUNCHER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class LauncherTests(unittest.TestCase):
    def test_launcher_flushes_the_url_for_noninteractive_callers(self):
        source = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("print(url, flush=True)", source)

    def test_launcher_builds_a_local_fragment_url(self):
        launcher = load_launcher()

        url = launcher.build_workbench_url(43123, "secret value")

        self.assertEqual(url, "http://127.0.0.1:43123/#token=secret+value")
        self.assertNotIn("?token", url)

    def test_launcher_prepares_a_loopback_server_with_a_distinct_token(self):
        launcher = load_launcher()
        with TemporaryDirectory() as temporary_directory:
            first = launcher.prepare_server(Path(temporary_directory), "0.1.0")
            second = launcher.prepare_server(Path(temporary_directory), "0.1.0")
            try:
                self.assertEqual(first[0].server_address[0], "127.0.0.1")
                self.assertNotEqual(first[1], second[1])
            finally:
                first[0].server_close()
                second[0].server_close()


if __name__ == "__main__":
    unittest.main()
