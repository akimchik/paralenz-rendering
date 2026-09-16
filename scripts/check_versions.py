#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# ///
import re
import sys
import os

def check_versions():
    errors = []
    
    # 1. Get version from README.md
    with open("README.md", "r") as f:
        readme = f.read()
    
    match = re.search(r"# Headless Dive Automation \(v(\d+\.\d+\.\d+)\)", readme)
    if not match:
        print("[ERROR] Could not find version in README.md")
        sys.exit(1)
    
    expected_version = match.group(1)
    print(f"[OK] Found canonical version v{expected_version} in README.md")

    # 2. Check SKILL.md
    with open("skill/paralenz-rendering/SKILL.md", "r") as f:
        skill = f.read()
    
    if f"Paralenz Rendering Standards (v{expected_version} Modular Architecture)" not in skill:
        errors.append(f"SKILL.md does not contain 'Paralenz Rendering Standards (v{expected_version} Modular Architecture)'")
    else:
        print(f"[OK] SKILL.md version matches (v{expected_version})")

    # 3. Check CHANGELOG.md
    with open("CHANGELOG.md", "r") as f:
        changelog = f.read()
    
    # Check if the latest version block matches
    cl_match = re.search(r"## \[v(\d+\.\d+\.\d+)\]", changelog)
    if not cl_match:
        errors.append("Could not parse latest version from CHANGELOG.md")
    elif cl_match.group(1) != expected_version:
        errors.append(f"CHANGELOG.md latest version is v{cl_match.group(1)}, expected v{expected_version}")
    else:
        print(f"[OK] CHANGELOG.md latest version matches (v{expected_version})")

    # 4. Check Branch Name (if in CI and not on main)
    # GitHub Actions sets GITHUB_REF_NAME to the branch name
    branch = os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", "")
    if branch and branch != "main" and "/v" in branch:
        # e.g. feat/v321-something -> 321
        b_match = re.search(r"/v(\d)(\d)(\d)-", branch)
        if b_match:
            b_version = f"{b_match.group(1)}.{b_match.group(2)}.{b_match.group(3)}"
            if b_version != expected_version:
                errors.append(f"Branch name '{branch}' implies v{b_version}, but files have v{expected_version}")
            else:
                print(f"[OK] Branch name '{branch}' matches version v{expected_version}")

    if errors:
        print("\n[ERROR] Version Mismatch Errors Found:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    
    print("\n[SUCCESS] All version strings are perfectly synchronized!")

if __name__ == "__main__":
    check_versions()
