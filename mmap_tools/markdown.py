"""Export/import between MindMap objects and Obsidian-compatible markdown.

Markdown format uses:
- Headings for top-level branches
- Nested lists for the topic tree
- Obsidian Tasks syntax for task metadata: 📅 due, ⏫ priority, ✅ done date
- Frontmatter for map metadata
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional

from .models import (
    MindMap,
    Task,
    TaskPriority,
    TaskStatus,
    Topic,
)


def to_markdown(mindmap: MindMap, *, include_frontmatter: bool = True) -> str:
    """Export a MindMap to Obsidian-compatible markdown.
    
    Args:
        mindmap: The map to export.
        include_frontmatter: Whether to include YAML frontmatter.
        
    Returns:
        Markdown string.
    """
    lines = []
    
    if include_frontmatter:
        lines.append("---")
        lines.append(f"title: \"{mindmap.root.text}\"")
        if mindmap._source_path:
            lines.append(f"source: \"{mindmap._source_path}\"")
        lines.append(f"exported: \"{datetime.now().strftime('%Y-%m-%d %H:%M')}\"")
        lines.append(f"topics: {mindmap.topic_count}")
        lines.append("---")
        lines.append("")
    
    lines.append(f"# {mindmap.root.text}")
    lines.append("")
    
    # Each top-level child becomes an H2
    for branch in mindmap.root.children:
        lines.append(f"## {branch.text}")
        lines.append("")
        
        for child in branch.children:
            _topic_to_md(child, lines, depth=0)
        
        lines.append("")
    
    return "\n".join(lines)


def _topic_to_md(topic: Topic, lines: list[str], depth: int) -> None:
    """Recursively render a topic as a markdown list item."""
    indent = "  " * depth
    
    # Build the line
    checkbox = ""
    task_meta = ""
    
    if topic.task is not None:
        t = topic.task
        if t.status == TaskStatus.COMPLETE:
            checkbox = "[x] "
        else:
            checkbox = "[ ] "
        
        meta_parts = []
        if t.priority == TaskPriority.HIGH:
            meta_parts.append("⏫")
        elif t.priority == TaskPriority.MEDIUM:
            meta_parts.append("🔼")
        elif t.priority == TaskPriority.LOW:
            meta_parts.append("🔽")
        
        if t.due_date:
            meta_parts.append(f"📅 {t.due_date.strftime('%Y-%m-%d')}")
        
        if t.percentage > 0 and t.percentage < 100:
            meta_parts.append(f"({t.percentage}%)")
        
        if meta_parts:
            task_meta = " " + " ".join(meta_parts)
    
    # Hyperlinks
    link_text = ""
    if topic.hyperlinks:
        links = [f"[🔗]({hl.url})" for hl in topic.hyperlinks]
        link_text = " " + " ".join(links)
    
    line = f"{indent}- {checkbox}{topic.text}{task_meta}{link_text}"
    lines.append(line)
    
    # Notes as blockquote
    if topic.note and topic.note.plain_text:
        for note_line in topic.note.plain_text.split("\n"):
            lines.append(f"{indent}  > {note_line}")
    
    # Children
    for child in topic.children:
        _topic_to_md(child, lines, depth + 1)


def from_markdown(text: str) -> MindMap:
    """Parse Obsidian-compatible markdown back into a MindMap.
    
    This is a best-effort parser for round-tripping. It handles:
    - H1 as root topic
    - H2 as top-level branches
    - Nested lists as topic trees
    - Obsidian Tasks checkbox syntax
    
    Args:
        text: Markdown string.
        
    Returns:
        A MindMap object.
    """
    lines = text.split("\n")
    mindmap = MindMap()
    
    # Skip frontmatter
    i = 0
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        i += 1  # Skip closing ---
    
    # Find H1 (root)
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("# ") and not line.startswith("## "):
            mindmap.root.text = line[2:].strip()
            break
        i += 1
    i += 1
    
    # Parse H2 sections
    current_branch = None
    list_stack: list[tuple[int, Topic]] = []  # (indent_level, topic)
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith("## "):
            # New top-level branch
            current_branch = Topic(text=stripped[3:].strip(), parent=mindmap.root)
            mindmap.root.children.append(current_branch)
            list_stack = []
        
        elif stripped.startswith("- "):
            if current_branch is None:
                i += 1
                continue
            
            # Calculate indent level
            indent = len(line) - len(line.lstrip())
            indent_level = indent // 2
            
            # Parse the list item
            topic = _parse_md_item(stripped[2:])
            
            # Find parent based on indent
            while list_stack and list_stack[-1][0] >= indent_level:
                list_stack.pop()
            
            if list_stack:
                parent = list_stack[-1][1]
            else:
                parent = current_branch
            
            topic.parent = parent
            parent.children.append(topic)
            list_stack.append((indent_level, topic))
        
        i += 1
    
    mindmap.title = mindmap.root.text
    return mindmap


def _parse_md_item(text: str) -> Topic:
    """Parse a markdown list item into a Topic."""
    topic = Topic()
    
    # Check for checkbox
    task = None
    if text.startswith("[x] "):
        task = Task(percentage=100)
        text = text[4:]
    elif text.startswith("[ ] "):
        task = Task()
        text = text[4:]
    
    # Extract task metadata
    if task is not None:
        # Priority
        if "⏫" in text:
            task.priority = TaskPriority.HIGH
            text = text.replace("⏫", "").strip()
        elif "🔼" in text:
            task.priority = TaskPriority.MEDIUM
            text = text.replace("🔼", "").strip()
        elif "🔽" in text:
            task.priority = TaskPriority.LOW
            text = text.replace("🔽", "").strip()
        
        # Due date
        due_match = re.search(r"📅\s*(\d{4}-\d{2}-\d{2})", text)
        if due_match:
            try:
                task.due_date = datetime.strptime(due_match.group(1), "%Y-%m-%d")
            except ValueError:
                pass
            text = text[:due_match.start()].strip() + text[due_match.end():].strip()
        
        # Percentage
        pct_match = re.search(r"\((\d+)%\)", text)
        if pct_match and task.percentage < 100:
            task.percentage = int(pct_match.group(1))
            text = text[:pct_match.start()].strip() + text[pct_match.end():].strip()
        
        topic.task = task
    
    # Extract hyperlinks [🔗](url)
    link_pattern = re.compile(r"\[🔗\]\(([^)]+)\)")
    for match in link_pattern.finditer(text):
        from .models import Hyperlink
        topic.hyperlinks.append(Hyperlink(url=match.group(1)))
    text = link_pattern.sub("", text).strip()
    
    topic.text = text.strip()
    return topic
