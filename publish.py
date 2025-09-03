# publish.py — create a branch, commit summary + artifacts, and open a PR.
import subprocess as sp
from pathlib import Path
from datetime import datetime
import sys, shlex

ROOT = Path(__file__).resolve().parent

def run(cmd, check=True):
    print(f"$ {cmd}")
    result = sp.run(cmd, shell=True, text=True, capture_output=True)
    if result.stdout: print(result.stdout.strip())
    if result.stderr: print(result.stderr.strip())
    if check and result.returncode != 0:
        sys.exit(f"❌ Command failed: {cmd}\n(exit {result.returncode})")
    return result

def default_base_branch():
    # Try to detect the remote default (main/master)
    r = run("git symbolic-ref refs/remotes/origin/HEAD", check=False)
    if r.returncode == 0 and r.stdout:
        ref = r.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref.split("/")[-1]
    # Fallbacks:
    for guess in ("main", "master"):
        r = run(f"git rev-parse --verify origin/{guess}", check=False)
        if r.returncode == 0:
            return guess
    return "main"

def find_summary():
    # Try common locations and reasonable fallbacks
    candidates = [
        ROOT / "docs" / "latest-sp800-summary.md",
        ROOT / "latest-sp800-summary.md",
        ROOT / "summary.md",
        ROOT / "source code" / "latest-sp800-summary.md",
        ROOT / "source code" / "summary.md",
    ]
    # Also pick any sp800*.md under docs/
    docs = ROOT / "docs"
    if docs.exists():
        for p in sorted(docs.glob("**/*sp800*.md")):
            candidates.append(p)
        for p in sorted(docs.glob("**/*summary*.md")):
            candidates.append(p)
    for p in candidates:
        if p.exists():
            return p
    return None

def main():
    # sanity
    run("git status -s", check=False)
    run("gh auth status", check=False)

    base = default_base_branch()
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    branch = f"chore/sp800-summary-{stamp}"

    # ensure required files exist
    summary_file = find_summary()
    if not summary_file:
        sys.exit("❌ No summary markdown found. Run Summary.py first (it should create a summary .md).")

    # optional artifacts to include if present
    artifacts = []
    for name in ("step1_nist_sp800_raw.json", "step2_filtered.json"):
        p = ROOT / name
        if p.exists():
            artifacts.append(p)

    print(f"Base branch: {base}")
    print(f"New branch:  {branch}")
    print(f"Summary:     {summary_file}")
    if artifacts:
        print("Artifacts:   " + ", ".join(str(a) for a in artifacts))

    # create branch
    run(f"git checkout -b {shlex.quote(branch)}")

    # ensure docs/ exists if your summary is under docs/
    if summary_file.parent != ROOT and not summary_file.parent.exists():
        summary_file.parent.mkdir(parents=True, exist_ok=True)

    # stage files
    add_targets = [summary_file] + artifacts
    quoted = " ".join(shlex.quote(str(p)) for p in add_targets)
    run(f"git add {quoted}")

    # commit
    title = f"NIST SP 800: latest summary ({stamp})"
    body  = (
        "Automated summary update.\n\n"
        "- Adds/updates latest SP 800 summary for software/DevOps/SDLC\n"
        "- Includes filtered artifacts for traceability\n"
        "- Generated in Codespaces\n"
    )
    run(f'git commit -m {shlex.quote(title)} -m {shlex.quote(body)}')

    # push & create PR
    run(f"git push -u origin {shlex.quote(branch)}")
    run(
        "gh pr create "
        f"--base {shlex.quote(base)} "
        f"--head {shlex.quote(branch)} "
        f"--title {shlex.quote(title)} "
        f"--body  {shlex.quote(body)}"
    )

    print("✅ PR opened. View it with:  gh pr view --web")
    run("gh pr view --web", check=False)

if __name__ == '__main__':
    main()
