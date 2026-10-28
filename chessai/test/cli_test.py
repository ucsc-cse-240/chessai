import os
import re

import edq.testing.asserts
import edq.testing.cli
import edq.testing.unittest

THIS_DIR: str = os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
BASE_TESTDATA_DIR: str = os.path.join(THIS_DIR, "testdata", "cli")
TEST_CASES_DIR: str = os.path.join(BASE_TESTDATA_DIR, "tests")
DATA_DIR: str = os.path.join(BASE_TESTDATA_DIR, "data")

def tournament_output_equals(test: edq.testing.unittest.BaseTest, expected: str, actual: str) -> None:
    """Compare tournament TSV output while normalizing numeric duration cells."""

    actual = re.sub(r'\t\d+(?:\.\d+)?\t\t$', r'\t<DURATION_SECONDS>\t\t', actual, flags = re.MULTILINE)
    edq.testing.asserts.content_equals_normalize(test, expected, actual)

class CLITest(edq.testing.unittest.BaseTest):
    """ Test CLI invocations. """

# Populate CLITest with all the test methods.
edq.testing.cli.discover_test_cases(CLITest, TEST_CASES_DIR, DATA_DIR)
