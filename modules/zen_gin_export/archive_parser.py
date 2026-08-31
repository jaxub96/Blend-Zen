"""
Parser for the ZenGin ASCII archive format - the inverse of
zen_gin_data_printer.py's writer. Produces a tree of ArchiveBlock nodes.

Pure string processing, no Blender dependency - same design principle as
coordinate_transform.py and archive_verifier.py, so this can be tested
and reused without needing Blender or mathutils.
"""

import re
from dataclasses import dataclass, field


_BLOCK_OPEN_RE = re.compile(r'^\s*\[(\S+)\s+(\S+)\s+(\d+)\s+(\d+)\]')
_PROPERTY_RE = re.compile(r'^\s*([^=\[\]]+)=([^:]+):(.*)$')


@dataclass
class ArchiveBlock:
    type1: str
    type2: str
    triangles_limit: int
    object_index: int
    properties: dict = field(default_factory=dict)
    property_types: dict = field(default_factory=dict)
    children: list = field(default_factory=list)

    def get(self, name, default=None):
        return self.properties.get(name, default)


def parse_archive(text):
    """Parse full archive text (header + body) into a list of top-level
    blocks (normally just the single oCWorld block)."""
    lines = text.splitlines()

    # body starts right after the header's second "END" marker, matching
    # the writer's exact header shape in zen_gin_zen_archive.py
    end_count = 0
    body_start = 0
    for i, line in enumerate(lines):
        if line.strip() == "END":
            end_count += 1
            if end_count == 2:
                body_start = i + 1
                break

    stack = []
    roots = []

    for line in lines[body_start:]:
        if not line.strip():
            continue

        if line.strip() == "[]":
            if stack:
                finished = stack.pop()
                if stack:
                    stack[-1].children.append(finished)
                else:
                    roots.append(finished)
            continue

        m = _BLOCK_OPEN_RE.match(line)
        if m:
            stack.append(ArchiveBlock(
                type1=m.group(1),
                type2=m.group(2),
                triangles_limit=int(m.group(3)),
                object_index=int(m.group(4)),
            ))
            continue

        m = _PROPERTY_RE.match(line)
        if m and stack:
            name, ptype, value = m.group(1).strip(), m.group(2).strip(), m.group(3)
            stack[-1].properties[name] = value
            stack[-1].property_types[name] = ptype

    return roots


def find_block(block, type1=None, type2=None):
    """First direct child matching the given type1/type2 (either can be
    None to mean 'any')."""
    for child in block.children:
        if (type1 is None or child.type1 == type1) and (type2 is None or child.type2 == type2):
            return child
    return None


def parse_vec3(value):
    return tuple(float(v) for v in value.split())
