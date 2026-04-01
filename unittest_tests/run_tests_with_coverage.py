#!/usr/bin/env python
"""Run all unittest tests with coverage measurement.

Runs each test module in a subprocess to guarantee full mock isolation
between test files (avoids sys.modules-level mock leakage).
"""
import subprocess
import sys
import os
import re
import glob

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
os.chdir(project_root)

try:
    import coverage
except ImportError:
    print("ERROR: 'coverage' package not installed. Run: pip install coverage")
    sys.exit(1)

# Clean up old coverage files
for f in glob.glob(os.path.join(project_root, '.coverage.*')):
    os.remove(f)
cov_file = os.path.join(project_root, '.coverage')
if os.path.exists(cov_file):
    os.remove(cov_file)

# Collect all test modules
test_dir = os.path.join(script_dir, 'unit')
test_files = sorted(f for f in os.listdir(test_dir) if f.startswith('test_') and f.endswith('.py'))

print("=" * 70)
print(f"Running {len(test_files)} test modules in isolated subprocesses")
print("=" * 70)

# Run each test module in a subprocess with its own coverage file
total_tests = 0
total_failures = 0
total_errors = 0
all_passed = True
cov_index = 0

for test_file in test_files:
    module_name = test_file[:-3]  # strip .py
    cov_data_file = os.path.join(project_root, f'.coverage.unit_{module_name}')

    cmd = [
        sys.executable, "-m", "coverage", "run",
        "--data-file", cov_data_file,
        "--source", os.path.join(project_root, 'src'),
        "--omit", "*/unittest_tests/*,*/tests/*,*/__pycache__/*",
        "--branch",
        "-m", "unittest", f"unittest_tests.unit.{module_name}",
        "-v"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)

    # Parse output for test counts
    output = result.stdout + result.stderr
    match = re.search(r'Ran (\d+) test', output)
    if match:
        count = int(match.group(1))
        total_tests += count

    if result.returncode != 0:
        all_passed = False
        fail_match = re.search(r'failures=(\d+)', output)
        err_match = re.search(r'errors=(\d+)', output)
        total_failures += int(fail_match.group(1)) if fail_match else 0
        total_errors += int(err_match.group(1)) if err_match else 0
        status = "FAIL"
        fail_info = ""
        if fail_match:
            fail_info += f" {fail_match.group(1)} failures"
        if err_match:
            fail_info += f" {err_match.group(1)} errors"
        print(f"  {module_name}: {status}{fail_info}")
    else:
        print(f"  {module_name}: OK")
    cov_index += 1

# Combine all coverage data files
print("\n" + "=" * 70)
print("COVERAGE REPORT")
print("=" * 70)

cov_files = glob.glob(os.path.join(project_root, '.coverage.unit_*'))
if cov_files:
    combine_result = subprocess.run(
        [sys.executable, "-m", "coverage", "combine"] + cov_files,
        capture_output=True, text=True, cwd=project_root
    )
    if combine_result.returncode != 0:
        print("Warning: coverage combine had issues:", combine_result.stderr)

report_result = subprocess.run(
    [sys.executable, "-m", "coverage", "report", "--show-missing"],
    capture_output=True, text=True, cwd=project_root
)
print(report_result.stdout)

# Generate HTML report
html_dir = os.path.join(script_dir, 'reports', 'html')
os.makedirs(html_dir, exist_ok=True)
subprocess.run(
    [sys.executable, "-m", "coverage", "html", "-d", html_dir],
    capture_output=True, text=True, cwd=project_root
)
print(f'HTML report generated: {html_dir}/index.html')

# Extract total coverage from report
for line in report_result.stdout.split('\n'):
    if line.startswith('TOTAL'):
        parts = line.split()
        if len(parts) >= 4:
            pct_str = parts[-1].rstrip('%')
            try:
                overall_pct = float(pct_str)
                print(f'\nOverall Coverage: {overall_pct:.1f}%')

                COVERAGE_THRESHOLD = 90
                if overall_pct < COVERAGE_THRESHOLD:
                    print(f'WARNING: Coverage {overall_pct:.1f}% is below {COVERAGE_THRESHOLD}% threshold')
                else:
                    print(f'Coverage meets {COVERAGE_THRESHOLD}%+ threshold!')
            except ValueError:
                pass
        break

# Clean up per-module coverage files
for f in cov_files:
    try:
        os.remove(f)
    except Exception:
        pass

# Summary
print(f'\nTotal: {total_tests} tests, {total_failures} failures, {total_errors} errors')

if not all_passed:
    print(f'\nSome tests failed. Run individual modules for details.')
    sys.exit(1)
else:
    print('\nAll tests passed!')
    sys.exit(0)
