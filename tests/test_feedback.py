import pytest
from codeguard.feedback import (
    FeedbackReport, TestResultParser, LintResultParser,
    FeedbackInjector, TestFailure,
)


pytest_output_pass = """
============================= test session starts ==============================
collected 3 items

test_example.py ...                                                      [100%]

============================== 3 passed in 0.05s ===============================
"""

pytest_output_fail = """
============================= test session starts ==============================
collected 3 items

test_example.py .F.                                                      [100%]

=================================== FAILURES ===================================
________________________________ test_add ____________________________________

    def test_add():
>       assert add(1, 2) == 4
E       assert 3 == 4

test_example.py:5: AssertionError
========================= 1 failed, 2 passed in 0.05s ==========================
"""

lint_output = """
src/main.py:10:1: F401 'os' imported but unused
src/main.py:25:80: E501 line too long (92 > 79 characters)
src/utils.py:5:1: F841 local variable 'x' is assigned to but never used
"""


class TestFeedbackReport:
    def test_clean_report(self):
        report = FeedbackReport(source="pytest", is_clean=True, summary="All good")
        assert report.is_clean
        assert report.source == "pytest"

    def test_dirty_report(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 failed",
            failures=[TestFailure(name="test_add", message="assert 3 == 4", file="test_example.py", line=5)],
        )
        assert not report.is_clean
        assert len(report.failures) == 1


class TestTestResultParser:
    def test_parse_passing_output(self):
        report = TestResultParser.parse(pytest_output_pass)
        assert report.is_clean
        assert "3 passed" in report.summary

    def test_parse_failing_output(self):
        report = TestResultParser.parse(pytest_output_fail)
        assert not report.is_clean
        assert "1 failed" in report.summary
        assert len(report.failures) == 1
        assert report.failures[0].name == "test_add"
        assert "assert 3 == 4" in report.failures[0].message

    def test_parse_empty_output(self):
        report = TestResultParser.parse("")
        assert report.is_clean


class TestLintResultParser:
    def test_parse_lint_output(self):
        report = LintResultParser.parse(lint_output)
        assert not report.is_clean
        assert len(report.failures) == 3
        assert report.failures[0].file == "src/main.py"
        assert report.failures[0].line == 10

    def test_parse_empty_lint_output(self):
        report = LintResultParser.parse("")
        assert report.is_clean

    def test_parse_clean_lint_output(self):
        report = LintResultParser.parse("All checks passed!")
        assert report.is_clean


class TestFeedbackInjector:
    def test_inject_feedback(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 test failed",
            failures=[TestFailure(name="test_add", message="assert 3 == 4", file="test_example.py", line=5)],
        )
        feedback = FeedbackInjector.inject(report)
        assert "test_add" in feedback
        assert "test_example.py" in feedback
        assert "assert 3 == 4" in feedback

    def test_inject_clean_feedback(self):
        report = FeedbackReport(source="pytest", is_clean=True, summary="All passed")
        feedback = FeedbackInjector.inject(report)
        assert "passed" in feedback.lower()

    def test_format_for_llm(self):
        report = FeedbackReport(
            source="pytest",
            is_clean=False,
            summary="1 failed",
            failures=[TestFailure(name="test_add", message="error", file="f.py", line=1)],
        )
        msg = FeedbackInjector.format_for_llm(report)
        assert "test_add" in msg
        assert "ACTION:" in msg