"""
Structural self-check for an exported ZenGin archive.

Every object block in the ASCII archive format needs a globally unique
sequential index (see ARCHITECTURE.md's "object-index thread" section -
this is flagged there as the highest-risk spot for future extension
bugs). This module verifies that invariant holds, and that the header's
claimed object count actually matches what's in the file.

This exact check - written ad hoc as a one-off debugging script while
diagnosing a real exported file - caught a genuine structural question
during development. It's built in here permanently instead of staying a
one-time favor, so every export gets checked for free.

Pure string/regex processing - no Blender dependency, fully testable
with plain pytest.

KNOWN LIMITATION: block shapes that always print index 0 as a structural
placeholder (VobTree, WayNet, ai, the empty "visual" sub-block used by
NoVisualObjectVob, EndMarker) are recognized by an explicit list of
(type1, type2) pairs below, not inferred generically. A future vob type
that introduces a new kind of always-zero wrapper block would need a
matching entry added here, or it will be (harmlessly, but confusingly)
flagged as a duplicate-index-0 issue.
"""

import re
from dataclasses import dataclass, field


_BLOCK_OPEN_RE = re.compile(r'^\s*\[(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\]')
_HEADER_COUNT_RE = re.compile(r'objects\s+(\d+)')

# (type1, type2) pairs that always print with object_index=0 as a
# structural placeholder, and never represent a real allocated object.
_ALWAYS_ZERO_WRAPPERS = {
    ("VobTree", "%"),
    ("WayNet", "%"),
    ("ai", "%"),
    ("visual", "%"),
}


@dataclass
class ArchiveVerificationResult:
    ok: bool
    header_object_count: int = None
    real_object_indices: list = field(default_factory=list)
    issues: list = field(default_factory=list)


def verify_archive_text(text):
    """Verify an already-loaded archive's text. See module docstring for
    what's checked and its known limitation."""
    issues = []

    header_match = _HEADER_COUNT_RE.search(text)
    header_count = int(header_match.group(1)) if header_match else None
    if header_count is None:
        issues.append("Could not find 'objects N' in the archive header")

    real_indices = []
    for line in text.splitlines():
        m = _BLOCK_OPEN_RE.match(line)
        if not m:
            continue
        type1, type2, _triangles, index = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))

        if type2 == "\u00a7":
            continue  # reused reference (waynet dedup marker), not a new allocation
        if (type1, type2) in _ALWAYS_ZERO_WRAPPERS and index == 0:
            continue
        if type1 == "EndMarker" and index == 0:
            continue

        real_indices.append(index)

    duplicates = sorted({i for i in real_indices if real_indices.count(i) > 1})
    if duplicates:
        issues.append(f"Duplicate object indices found: {duplicates}")

    sorted_unique = sorted(set(real_indices))
    expected = list(range(len(sorted_unique)))
    if sorted_unique != expected:
        shown = sorted_unique[:20]
        issues.append(
            "Object indices are not contiguous from 0: got "
            f"{shown}{' ...' if len(sorted_unique) > 20 else ''}"
        )

    if header_count is not None and len(sorted_unique) != header_count:
        issues.append(
            f"Header claims {header_count} objects, but {len(sorted_unique)} "
            "distinct object indices were found in the body"
        )

    return ArchiveVerificationResult(
        ok=(len(issues) == 0),
        header_object_count=header_count,
        real_object_indices=sorted_unique,
        issues=issues,
    )


def verify_archive_file(filepath, encoding="windows-1250"):
    """Verify an exported .ZEN file on disk."""
    with open(filepath, "r", encoding=encoding) as f:
        text = f.read()
    return verify_archive_text(text)
