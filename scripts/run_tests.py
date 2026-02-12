#!/usr/bin/env python
"""
Test runner script for DoomStopper
Run tests with various configurations
"""
import sys
import subprocess


def run_command(cmd):
    """Run a command and return exit code"""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"

    if test_type == "quick":
        # Quick test run without coverage
        return run_command(["pytest", "-v"])

    elif test_type == "coverage":
        # Run tests with coverage report
        return run_command([
            "pytest",
            "-v",
            "--cov=.",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])

    elif test_type == "unit":
        # Run only unit tests
        return run_command(["pytest", "-v", "-m", "unit"])

    elif test_type == "integration":
        # Run only integration tests
        return run_command(["pytest", "-v", "-m", "integration"])

    elif test_type == "file":
        # Run specific test file
        if len(sys.argv) < 3:
            print("Usage: python run_tests.py file <test_file>")
            return 1
        return run_command(["pytest", "-v", sys.argv[2]])

    elif test_type == "all":
        # Run all tests with coverage
        return run_command([
            "pytest",
            "-v",
            "--cov=.",
            "--cov-report=term-missing"
        ])

    else:
        print(f"Unknown test type: {test_type}")
        print("\nAvailable options:")
        print("  all        - Run all tests with coverage (default)")
        print("  quick      - Run tests without coverage")
        print("  coverage   - Run tests with HTML coverage report")
        print("  unit       - Run only unit tests")
        print("  integration - Run only integration tests")
        print("  file <path> - Run specific test file")
        return 1


if __name__ == "__main__":
    sys.exit(main())