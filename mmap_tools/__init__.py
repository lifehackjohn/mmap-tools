"""mmap-tools: Read, write, and convert MindManager .mmap files.

A pure Python library for working with MindJet MindManager mind map files.
No external dependencies required.

Usage:
    import mmap_tools
    
    # Read a mind map
    m = mmap_tools.read("ToDo List.mmap")
    print(m)  # MindMap('ToDo', 186 topics)
    
    # Navigate the tree
    for topic in m.root.children:
        print(topic.text, len(topic.children))
    
    # Find topics
    health = m.find("01 Health & Fitness")
    for item in health.walk():
        print("  " * item.depth + item.text)
    
    # Export to markdown
    md = mmap_tools.to_markdown(m)
    
    # Write back to .mmap
    mmap_tools.write(m, "output.mmap")
"""

__version__ = "0.1.0"

from .reader import read
from .writer import write
from .markdown import to_markdown, from_markdown
from .models import MindMap, Topic, Task, TaskPriority, TaskStatus, IconMarker, Hyperlink, Note

__all__ = [
    "read",
    "write", 
    "to_markdown",
    "from_markdown",
    "MindMap",
    "Topic",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "IconMarker",
    "Hyperlink",
    "Note",
]
