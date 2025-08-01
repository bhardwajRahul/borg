# Note: these tests are part of the self test, do not use or import pytest functionality here.
#       See borg.selftest for details. If you add/remove test methods, update SELFTEST_COUNT

"""
Self testing module
===================

The selftest() function runs a small test suite of relatively fast tests that are meant to discover issues
with the way Borg was compiled or packaged and also bugs in Borg itself.

These tests are a subset of the borg/testsuite and are run with Pythons built-in unittest, hence none of
the tests used for this can or should be ported to py.test currently.

To assert that self test discovery works correctly the number of tests is kept in the SELFTEST_COUNT
variable. SELFTEST_COUNT must be updated if new tests are added or removed to or from any of the tests
used here.
"""

import os
import sys
import time
from unittest import TestResult, TestSuite, defaultTestLoader

from .testsuite.crypto.crypto_test import CryptoTestCase
from .testsuite.chunkers.buzhash_self_test import ChunkerTestCase
from .testsuite.chunkers.fixed_self_test import ChunkerFixedTestCase

SELFTEST_CASES = [CryptoTestCase, ChunkerTestCase, ChunkerFixedTestCase]

SELFTEST_COUNT = 17


class SelfTestResult(TestResult):
    def __init__(self):
        super().__init__()
        self.successes = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.successes.append(test)

    def test_name(self, test):
        return test.shortDescription() or str(test)

    def log_results(self, logger):
        for test, failure in self.errors + self.failures + self.unexpectedSuccesses:
            logger.error("self test %s FAILED:\n%s", self.test_name(test), failure)
        for test, reason in self.skipped:
            logger.warning("self test %s skipped: %s", self.test_name(test), reason)

    def successful_test_count(self):
        return len(self.successes)


def selftest(logger):
    if os.environ.get("BORG_SELFTEST") == "disabled":
        logger.debug("borg selftest disabled via BORG_SELFTEST env variable")
        return
    selftest_started = time.perf_counter()
    result = SelfTestResult()
    test_suite = TestSuite()
    for test_case in SELFTEST_CASES:
        module = sys.modules[test_case.__module__]
        # a normal borg user does not have pytest installed, we must not require it in the test modules used here.
        # note: this only detects the usual toplevel import
        assert "pytest" not in dir(module), "pytest must not be imported in %s" % module.__name__
        test_suite.addTest(defaultTestLoader.loadTestsFromTestCase(test_case))
    test_suite.run(result)
    result.log_results(logger)
    successful_tests = result.successful_test_count()
    count_mismatch = successful_tests != SELFTEST_COUNT
    if result.wasSuccessful() and count_mismatch:
        # only print this if all tests succeeded
        logger.error(
            "self test count (%d != %d) mismatch, either test discovery is broken or a test was added "
            "without updating borg.selftest",
            successful_tests,
            SELFTEST_COUNT,
        )
    if not result.wasSuccessful() or count_mismatch:
        logger.error(
            "self test failed\n"
            "Could be a bug either in Borg, the package / distribution you use, your OS or your hardware."
        )
        sys.exit(2)
        assert False, "sanity assertion failed: ran beyond sys.exit()"
    selftest_elapsed = time.perf_counter() - selftest_started
    logger.debug("%d self tests completed in %.2f seconds", successful_tests, selftest_elapsed)
