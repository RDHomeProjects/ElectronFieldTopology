"""Check documentation structure without third-party dependencies.

Software licence: Apache-2.0. Does not validate remote links or physics.
"""
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "README.md", "AGENTS.md", "CONTRIBUTING.md", "LICENSE", "LICENSE-DOCS.md",
    "NOTICE", "CITATION.cff", "docs/README.md", "docs/STATUS.md",
    "docs/01-purpose-and-scope.md", "docs/02-physics-and-hypotheses.md",
    "docs/03-requirements.md", "docs/04-architecture.md",
    "docs/05-ai-development.md", "docs/06-development-plan.md",
    "docs/07-validation.md", "docs/literature/README.md",
    "docs/literature/references.bib", "docs/decisions/README.md",
    "docs/templates/model.md", "docs/templates/experiment-report.md",
    ".github/workflows/docs.yml",
)
LINK = re.compile(r"!?\[[^\]\n]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")


def check(root=ROOT):
    errors = []
    for item in REQUIRED:
        if not (root / item).is_file():
            errors.append(f"Missing required file: {item}")
    paths = [
        path for path in root.rglob("*.md")
        if not any(part in {".git", ".venv", "artifacts", "node_modules"}
                   for part in path.relative_to(root).parts)
    ]
    for path in paths:
        fence = None
        visible = []
        for line in path.read_text(encoding="utf-8").splitlines():
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            if marker:
                token = marker.group(1)
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                continue
            if fence is None:
                visible.append(line)
        if fence:
            errors.append(f"Unclosed code fence: {path.relative_to(root)}")
        for target in LINK.findall("\n".join(visible)):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            resolved = (path.parent / unquote(parsed.path)).resolve()
            if not resolved.is_relative_to(root.resolve()):
                errors.append(f"Link escapes repository: {target}")
            elif not resolved.exists():
                errors.append(f"Broken link in {path.relative_to(root)}: {target}")
    return errors, len(paths)


if __name__ == "__main__":
    failures, count = check()
    for failure in failures:
        print(failure, file=sys.stderr)
    if failures:
        raise SystemExit(1)
    print(f"Documentation checks passed: {count} Markdown files; local targets and fences.")
