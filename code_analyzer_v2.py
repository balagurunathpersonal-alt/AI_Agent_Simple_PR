import re

from review_models_v2 import (
    FindingSource,
    ReviewFinding,
    Severity,
)


class CodeAnalyzer:

    def analyze(
        self,
        filepath: str,
        content: str,
    ) -> list[ReviewFinding]:

        findings = []

        if filepath.endswith(".swift"):

            findings.extend(
                self._analyze_swift(
                    filepath,
                    content,
                )
            )

        return findings

    # ========================================================
    # Swift Analyzer
    # ========================================================

    def _analyze_swift(
        self,
        filepath: str,
        content: str,
    ) -> list[ReviewFinding]:

        findings = []

        lines = content.splitlines()

        findings.extend(
            self._detect_try_force(
                filepath,
                lines,
            )
        )

        findings.extend(
            self._detect_force_cast(
                filepath,
                lines,
            )
        )

        findings.extend(
            self._detect_fatal_error(
                filepath,
                lines,
            )
        )

        findings.extend(
            self._detect_precondition_failure(
                filepath,
                lines,
            )
        )

        findings.extend(
            self._detect_unreachable_code(
                filepath,
                lines,
            )
        )

        return findings

    # ========================================================
    # try!
    # ========================================================

    def _detect_try_force(
        self,
        filepath: str,
        lines: list[str],
    ) -> list[ReviewFinding]:

        findings = []

        for index, line in enumerate(
            lines,
            start=1,
        ):

            if "try!" not in line:
                continue

            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    category="Correctness",
                    file=filepath,
                    line_number=index,
                    title=(
                        "Forced try can crash "
                        "the application"
                    ),
                    explanation=(
                        "The code uses `try!`. "
                        "If the operation throws an error, "
                        "the application will terminate."
                    ),
                    why_it_matters=(
                        "Recoverable runtime failures can "
                        "become production crashes."
                    ),
                    suggested_fix=(
                        "Use do/catch, optional try (`try?`), "
                        "or propagate the error using `throws`."
                    ),
                    source=(
                        FindingSource
                        .STATIC_ANALYZER
                    ),
                )
            )

        return findings

    # ========================================================
    # as!
    # ========================================================

    def _detect_force_cast(
        self,
        filepath: str,
        lines: list[str],
    ) -> list[ReviewFinding]:

        findings = []

        for index, line in enumerate(
            lines,
            start=1,
        ):

            if " as! " not in line:
                continue

            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    category="Correctness",
                    file=filepath,
                    line_number=index,
                    title="Unsafe forced type cast",
                    explanation=(
                        "The code uses `as!`, which "
                        "will crash if the runtime value "
                        "is not of the expected type."
                    ),
                    why_it_matters=(
                        "Unexpected runtime data can "
                        "cause an immediate crash."
                    ),
                    suggested_fix=(
                        "Use `as?` and safely handle "
                        "the optional cast result."
                    ),
                    source=(
                        FindingSource
                        .STATIC_ANALYZER
                    ),
                )
            )

        return findings

    # ========================================================
    # fatalError
    # ========================================================

    def _detect_fatal_error(
        self,
        filepath: str,
        lines: list[str],
    ) -> list[ReviewFinding]:

        findings = []

        for index, line in enumerate(
            lines,
            start=1,
        ):

            if "fatalError(" not in line:
                continue

            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    category="Crash Risk",
                    file=filepath,
                    line_number=index,
                    title="fatalError can terminate the app",
                    explanation=(
                        "This code explicitly terminates "
                        "execution by calling fatalError()."
                    ),
                    why_it_matters=(
                        "If this path is reachable in "
                        "production, the application "
                        "will crash."
                    ),
                    suggested_fix=(
                        "Replace fatalError with recoverable "
                        "error handling unless this path is "
                        "provably impossible in production."
                    ),
                    source=(
                        FindingSource
                        .STATIC_ANALYZER
                    ),
                )
            )

        return findings

    # ========================================================
    # preconditionFailure
    # ========================================================

    def _detect_precondition_failure(
        self,
        filepath: str,
        lines: list[str],
    ) -> list[ReviewFinding]:

        findings = []

        for index, line in enumerate(
            lines,
            start=1,
        ):

            if (
                "preconditionFailure("
                not in line
            ):
                continue

            findings.append(
                ReviewFinding(
                    severity=Severity.HIGH,
                    category="Crash Risk",
                    file=filepath,
                    line_number=index,
                    title=(
                        "preconditionFailure "
                        "can terminate execution"
                    ),
                    explanation=(
                        "The code contains an explicit "
                        "precondition failure."
                    ),
                    why_it_matters=(
                        "If the condition is reachable, "
                        "the process can terminate."
                    ),
                    suggested_fix=(
                        "Use recoverable validation/error "
                        "handling where appropriate."
                    ),
                    source=(
                        FindingSource
                        .STATIC_ANALYZER
                    ),
                )
            )

        return findings

    # ========================================================
    # Unreachable Code
    # ========================================================

    def _detect_unreachable_code(
        self,
        filepath: str,
        lines: list[str],
    ) -> list[ReviewFinding]:

        findings = []

        brace_depth = 0
        return_depth = None

        for index, raw_line in enumerate(
            lines,
            start=1,
        ):

            stripped = raw_line.strip()

            if not stripped:
                continue

            # Ignore comments.
            if stripped.startswith("//"):
                continue

            # If we previously encountered return,
            # detect executable statements before
            # leaving the current scope.
            if return_depth is not None:

                if (
                    brace_depth >= return_depth
                    and not stripped.startswith("}")
                ):

                    findings.append(
                        ReviewFinding(
                            severity=Severity.HIGH,
                            category="Control Flow",
                            file=filepath,
                            line_number=index,
                            title=(
                                "Unreachable code after "
                                "return statement"
                            ),
                            explanation=(
                                "This statement appears after "
                                "an unconditional `return` "
                                "within the same scope, so it "
                                "will never execute."
                            ),
                            why_it_matters=(
                                "Expected logic can silently "
                                "be skipped, resulting in "
                                "incorrect application behavior."
                            ),
                            suggested_fix=(
                                "Move the statement before the "
                                "return, or restructure the "
                                "control flow so it can execute."
                            ),
                            source=(
                                FindingSource
                                .STATIC_ANALYZER
                            ),
                        )
                    )

                    # Report only first unreachable line
                    # for this return block.
                    return_depth = None

            # Detect return.
            if re.match(
                r"^return\b",
                stripped,
            ):

                return_depth = brace_depth

            # Update brace depth last.
            brace_depth += raw_line.count("{")
            brace_depth -= raw_line.count("}")

            if (
                return_depth is not None
                and brace_depth < return_depth
            ):

                return_depth = None

        return findings