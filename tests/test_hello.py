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


if __name__ == "__main__":
    unittest.main()
