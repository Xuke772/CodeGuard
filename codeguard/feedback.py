import re
from dataclasses import dataclass, field


@dataclass
class TestFailure:
    name: str = ""
    message: str = ""
    file: str = ""
    line: int = 0


@dataclass
class FeedbackReport:
    source: str
    is_clean: bool
    summary: str
    failures: list[TestFailure] = field(default_factory=list)


class TestResultParser:
    @staticmethod
    def parse(output: str) -> FeedbackReport:
        if not output:
            return FeedbackReport(source="pytest", is_clean=True, summary="No test output")
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        error_match = re.search(r"(\d+)\s+error", output)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0
        errors = int(error_match.group(1)) if error_match else 0
        total_failures = failed + errors
        if total_failures == 0 and passed > 0:
            return FeedbackReport(source="pytest", is_clean=True, summary=f"{passed} passed")
        failures = []
        for match in re.finditer(r"_{10,}\s+(\w+)\s+_{10,}", output):
            test_name = match.group(1)
            start = match.end()
            next_test = re.search(r"_{10,}\s+\w+\s+_{10,}", output[start:])
            end = start + next_test.start() if next_test else len(output)
            block = output[start:end]
            f = TestFailure(name=test_name)
            error_match = re.search(r"E\s+(.+?)$", block, re.MULTILINE)
            if error_match:
                f.message = error_match.group(1).strip()
            file_match = re.search(r"(\S+\.py):(\d+):", block)
            if file_match:
                f.file = file_match.group(1)
                f.line = int(file_match.group(2))
            failures.append(f)
        return FeedbackReport(
            source="pytest",
            is_clean=False,
            summary=f"{total_failures} failed, {passed} passed",
            failures=failures,
        )


class LintResultParser:
    @staticmethod
    def parse(output: str) -> FeedbackReport:
        if not output.strip():
            return FeedbackReport(source="lint", is_clean=True, summary="No lint issues")
        if "passed" in output.lower() or "no issues" in output.lower():
            return FeedbackReport(source="lint", is_clean=True, summary="All checks passed")
        failures = []
        pattern = re.compile(r"^(.+?):(\d+):(\d+)?:?\s*(\w+)\s+(.+)$", re.MULTILINE)
        for match in pattern.finditer(output):
            failures.append(TestFailure(
                file=match.group(1),
                line=int(match.group(2)),
                name=match.group(4),
                message=match.group(5).strip(),
            ))
        if not failures:
            return FeedbackReport(source="lint", is_clean=True, summary="No lint issues")
        return FeedbackReport(
            source="lint",
            is_clean=False,
            summary=f"{len(failures)} lint issues found",
            failures=failures,
        )


class FeedbackInjector:
    @staticmethod
    def inject(report: FeedbackReport) -> str:
        if report.is_clean:
            return f"[{report.source}] {report.summary}. No action needed."
        lines = [f"[{report.source}] {report.summary}:"]
        for f in report.failures:
            location = f"{f.file}:{f.line}" if f.file else "unknown"
            lines.append(f"  - {f.name} at {location}: {f.message}")
        return "\n".join(lines)

    @staticmethod
    def format_for_llm(report: FeedbackReport) -> str:
        if report.is_clean:
            return FeedbackInjector.inject(report)
        lines = [FeedbackInjector.inject(report)]
        lines.append("\nPlease fix the above failures. Use the following actions to investigate and fix:")
        lines.append("ACTION: 1. read_file to examine the failing file")
        lines.append("ACTION: 2. write_file to apply the fix")
        lines.append("ACTION: 3. run_tests to verify the fix")
        return "\n".join(lines)