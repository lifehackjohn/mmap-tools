# mmap-tools

[![Tests](https://github.com/lifehackjohn/mmap-tools/actions/workflows/test.yml/badge.svg)](https://github.com/lifehackjohn/mmap-tools/actions/workflows/test.yml)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-green.svg)](https://www.python.org/downloads/)

Read, write, and convert MindJet MindManager `.mmap` files. Pure Python, zero dependencies.

## Features

- **Read** `.mmap` files into a clean Python object model
- **Write** back to `.mmap` with round-trip fidelity (preserves styles, icons, layout)
- **Export** to Obsidian-compatible markdown (with Tasks plugin syntax)
- **Import** from markdown back to `.mmap`
- **CLI** for quick inspection and conversion
- **No dependencies** — only Python stdlib

## Install

```bash
pip install mmap-tools
```

## Quick Start

```python
import mmap_tools

# Read a mind map
m = mmap_tools.read("ToDo List.mmap")
print(m)  # MindMap('ToDo', 186 topics)

# Navigate the tree
for branch in m.root.children:
    print(f"{branch.text}: {len(branch.children)} children")

# Find topics
health = m.find("Health & Fitness")
for item in health.walk():
    print("  " * item.depth + item.text)

# List tasks
for topic in m.tasks(status=mmap_tools.TaskStatus.NOT_STARTED):
    print(f"TODO: {topic.text}")

# Modify
new_task = health.add_child("Book dentist appointment")
new_task.task = mmap_tools.Task(priority=mmap_tools.TaskPriority.HIGH)

# Export to markdown
md = mmap_tools.to_markdown(m)
print(md)

# Write back to .mmap
mmap_tools.write(m, "updated.mmap")
```

## CLI

```bash
# Show map summary
mmap-tools info "ToDo List.mmap"

# Print full tree
mmap-tools tree "ToDo List.mmap" --depth 3

# List open tasks
mmap-tools tasks "ToDo List.mmap" --status open

# Search
mmap-tools find "ToDo List.mmap" "insurance"

# Export to markdown
mmap-tools export "ToDo List.mmap" -o tasks.md
```

## How .mmap files work

MindManager `.mmap` files are ZIP archives containing:
- `Document.xml` — the map structure (topics, tasks, icons, notes, hyperlinks)
- `bin/` — embedded images and attachments
- `xsd/` — XML schema definitions
- `Preview.png` — thumbnail

This library reads and writes `Document.xml` while preserving all other contents.

## Obsidian Integration

The markdown export uses [Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks) syntax:

```markdown
- [ ] Book dentist ⏫ 📅 2026-03-15
- [x] Submit tax return
- [ ] Review insurance (25%)
```

Import back to `.mmap`:

```python
md = open("tasks.md").read()
m = mmap_tools.from_markdown(md)
mmap_tools.write(m, "from_obsidian.mmap")
```

## License

AGPL-3.0 — see [LICENSE](LICENSE)
