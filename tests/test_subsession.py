import unittest
import subsession
import sys
from pathlib import Path

import os

dummy_pkg_path = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(dummy_pkg_path))

non_pkg_path = Path(__file__).parent / "fixtures" / "non_pkg_folder"


class TestSubsession(unittest.TestCase):
    def setUp(self):
        self.a = None
        self.b = None
        self.c = None
        self.d = None

    def test_subsession_context_manager(self):
        import dummy_pkg as a

        with subsession.Session(
            env={"TEST_ENV": "test"},
            paths=[str(non_pkg_path)],
        ):
            import dummy_pkg as b

            self.assertEqual(os.environ["TEST_ENV"], "test")

            # just make sure it doesn't raise
            import non_findable_pkg

        with subsession.Session():
            import dummy_pkg as c

            with self.assertRaises(ImportError):
                import non_findable_pkg

        import dummy_pkg as d

        self.a = a
        self.b = b
        self.c = c
        self.d = d

        self.assert_isolated()

    def test_subsession_decorator(self):
        import dummy_pkg as a

        @subsession.Session(
            env={"TEST_ENV": "test"},
            paths=[str(non_pkg_path)],
        )
        def run_b():
            import dummy_pkg as b

            self.b = b
            self.assertEqual(os.environ["TEST_ENV"], "test")
            # just make sure it doesn't raise
            import non_findable_pkg

        @subsession.Session()
        def run_c():
            import dummy_pkg as c

            self.c = c

        import dummy_pkg as d

        run_b()
        run_c()
        self.a = a
        self.d = d

        self.assert_isolated()

    def test_subsession_internal_caching_import_after(self):
        with subsession.Session():
            import dummy_pkg as a
            import dummy_pkg as b
        import dummy_pkg as c

        self.assertIs(a, b)
        self.assertIsNot(a, c)

    def test_subsession_internal_caching_import_before(self):
        import dummy_pkg as a

        with subsession.Session():
            import dummy_pkg as b
            import dummy_pkg as c

        self.assertIs(b, c)
        self.assertIsNot(a, c)

    def test_subsession_keep_global_import_before(self):
        import dummy_pkg as a

        with subsession.Session(keep_global=["dummy_pkg"]):
            import dummy_pkg as b

        self.assertIs(a, b)

    def test_subsession_keep_global_import_after(self):
        with subsession.Session(keep_global=["dummy_pkg"]):
            import dummy_pkg as a

        import dummy_pkg as b

        self.assertIs(a, b)

    def test_subsession_reload(self):
        with subsession.Session() as s:
            import dummy_pkg as a
        func_before = a.runs_on_import
        s.reload(a)
        self.assertIsNot(func_before, a.runs_on_import)

    def assert_isolated(self):
        self.assertNotIn("TEST_ENV", os.environ)

        self.assertIsNot(self.a, self.b)
        self.assertIsNot(self.a, self.c)
        self.assertIsNot(self.b, self.c)
        self.assertIs(self.a, self.d)

        self.a.runs_on_import.assert_called_once()
        self.b.runs_on_import.assert_called_once()
        self.c.runs_on_import.assert_called_once()
