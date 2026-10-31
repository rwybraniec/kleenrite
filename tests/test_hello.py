"""Tests for the hello greeting function and CLI."""

import contextlib
import io
import unittest

from hello.cli import main
from hello.greet import greet


class GreetTests(unittest.TestCase):
    def test_default(self):
        self.assertEqual(greet(), "Hello, world!")

    def test_name(self):
        self.assertEqual(greet("Ada"), "Hello, Ada!")

    def test_shout(self):
        self.assertEqual(greet("Ada", shout=True), "HELLO, ADA!")

    def test_empty_name_falls_back_to_world(self):
        self.assertEqual(greet(""), "Hello, world!")

    def test_whitespace_name_falls_back_to_world(self):
        self.assertEqual(greet("   "), "Hello, world!")

    def test_surrounding_whitespace_stripped(self):
        self.assertEqual(greet("  Ada  "), "Hello, Ada!")


class MainTests(unittest.TestCase):
    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = main(argv)
        return code, buf.getvalue()

    def test_no_args(self):
        self.assertEqual(self.run_main([]), (0, "Hello, world!\n"))

    def test_name(self):
        self.assertEqual(self.run_main(["Ada"]), (0, "Hello, Ada!\n"))

    def test_shout(self):
        self.assertEqual(self.run_main(["Ada", "--shout"]), (0, "HELLO, ADA!\n"))

    def test_repeat(self):
        self.assertEqual(self.run_main(["Ada", "--repeat", "3"]), (0, "Hello, Ada!\n" * 3))

    def test_repeat_with_shout(self):
        self.assertEqual(
            self.run_main(["Ada", "--shout", "--repeat", "2"]), (0, "HELLO, ADA!\n" * 2)
        )

    def test_repeat_one_equals_default(self):
        self.assertEqual(self.run_main(["--repeat", "1"]), (0, "Hello, world!\n"))


class RepeatArgErrorTests(unittest.TestCase):
    def test_bad_repeat_values_exit_2(self):
        for value in ["0", "-1", "x", "2.5", ""]:
            with self.subTest(value=value):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as cm:
                    main(["--repeat", value])
                self.assertEqual(cm.exception.code, 2)
                self.assertIn("must be a positive integer", err.getvalue())


if __name__ == "__main__":
    unittest.main()
