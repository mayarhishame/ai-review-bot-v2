import re
from dataclasses import dataclass, field

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")

LANGUAGES = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java",
}

SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock"}
SKIP_SUFFIXES = (".min.js", ".lock", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".svg")


@dataclass
class DiffLine:
    kind: str            # "add" | "del" | "ctx"
    content: str
    old_no: int | None
    new_no: int | None


@dataclass
class Hunk:
    header: str
    lines: list[DiffLine] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    language: str | None
    hunks: list[Hunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False
    is_binary: bool = False

    @property
    def added_line_numbers(self) -> set[int]:
        """Line numbers (new file) that GitHub allows inline comments on."""
        return {
            l.new_no for h in self.hunks for l in h.lines
            if l.kind == "add" and l.new_no is not None
        }

    @property
    def reviewable(self) -> bool:
        name = self.path.rsplit("/", 1)[-1]
        return not (
            self.is_binary or self.is_deleted
            or name in SKIP_NAMES
            or self.path.endswith(SKIP_SUFFIXES)
            or self.language is None
        )


def detect_language(path: str) -> str | None:
    for ext, lang in LANGUAGES.items():
        if path.endswith(ext):
            return lang
    return None


def parse_diff(diff_text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    hunk: Hunk | None = None
    old_no = new_no = 0

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git "):
            m = re.match(r"diff --git a/(.*) b/(.*)$", raw)
            path = m.group(2) if m else raw.split(" b/")[-1]
            current = FileDiff(path=path, language=detect_language(path))
            files.append(current)
            hunk = None
            continue
        if current is None:
            continue

        m = HUNK_RE.match(raw)
        if m:
            old_no, new_no = int(m.group(1)), int(m.group(2))
            hunk = Hunk(header=raw)
            current.hunks.append(hunk)
        elif hunk is None:  # file header section
            if raw.startswith("new file mode"):
                current.is_new = True
            elif raw.startswith("deleted file mode"):
                current.is_deleted = True
            elif raw.startswith(("Binary files", "GIT binary patch")):
                current.is_binary = True
        else:  # inside a hunk
            if raw.startswith("+"):
                hunk.lines.append(DiffLine("add", raw[1:], None, new_no))
                new_no += 1
            elif raw.startswith("-"):
                hunk.lines.append(DiffLine("del", raw[1:], old_no, None))
                old_no += 1
            elif raw.startswith("\\"):   # "\ No newline at end of file"
                continue
            else:
                hunk.lines.append(DiffLine("ctx", raw[1:], old_no, new_no))
                old_no += 1
                new_no += 1
    return files


def render_for_prompt(f: FileDiff) -> str:
    """Show the LLM each line with its NEW line number so it can cite exact lines."""
    out = [f"FILE: {f.path} ({f.language})"]
    for h in f.hunks:
        out.append(h.header)
        for l in h.lines:
            if l.kind == "add":
                out.append(f"{l.new_no:>5} + {l.content}")
            elif l.kind == "del":
                out.append(f"      - {l.content}")
            else:
                out.append(f"{l.new_no:>5}   {l.content}")
    return "\n".join(out)


def chunk_files(files: list[FileDiff], max_chars: int) -> list[list[FileDiff]]:
    """Group reviewable files into batches that fit the LLM context budget."""
    chunks, current, size = [], [], 0
    for f in (f for f in files if f.reviewable):
        n = len(render_for_prompt(f))
        if current and size + n > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(f)
        size += n
    if current:
        chunks.append(current)
    return chunks