#!/usr/bin/env python3
"""VidyaBot evaluation runner — prints a summary report."""

import subprocess
import sys
import re


SUITES = [
    ("Security Tests", "evals/test_security.py"),
    ("Diagnostic Tests", "evals/test_diagnostic.py"),
    ("Assessment Tests", "evals/test_assessment.py"),
    ("Content Tests", "evals/test_content.py"),
]


def run_suite(name: str, path: str) -> tuple[int, int]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", path, "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    output = result.stdout + result.stderr
    passed = len(re.findall(r" PASSED", output))
    failed = len(re.findall(r" FAILED|ERROR", output))
    total = passed + failed
    if result.returncode != 0 and total == 0:
        print(f"  ⚠️  {name}: Could not run (check imports)")
        return 0, 0
    return passed, total


def main():
    print("\n" + "=" * 52)
    print("  VidyaBot Eval Report")
    print("=" * 52)

    grand_passed = 0
    grand_total = 0

    for name, path in SUITES:
        passed, total = run_suite(name, path)
        status = "✅ PASS" if passed == total and total > 0 else "❌ FAIL"
        pct = f"{passed/total*100:.0f}%" if total else "N/A"
        print(f"  {name:<22} {passed:>3}/{total:<3} {status} ({pct})")
        grand_passed += passed
        grand_total += total

    print("=" * 52)
    overall_pct = f"{grand_passed/grand_total*100:.0f}%" if grand_total else "N/A"
    final = "✅ ALL PASS" if grand_passed == grand_total and grand_total > 0 else "❌ FAILURES"
    print(f"  {'Overall':<22} {grand_passed:>3}/{grand_total:<3} {final} ({overall_pct})")
    print("=" * 52 + "\n")

    sys.exit(0 if grand_passed == grand_total and grand_total > 0 else 1)


if __name__ == "__main__":
    main()
