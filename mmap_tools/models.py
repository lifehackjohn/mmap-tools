"""Data models for MindManager .mmap files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class TaskPriority(Enum):
    """MindManager task priority levels."""
    NONE = ""
    HIGH = "1"
    MEDIUM = "2" 
    LOW = "3"


class TaskStatus(Enum):
    """Derived task status from percentage."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


@dataclass
class IconMarker:
    """An icon/marker attached to a topic."""
    icon_type: str = ""
    icon_signature: str = ""
    
    # Well-known icon types
    PRIORITY_1 = "urn:mindjet:Priority1"
    PRIORITY_2 = "urn:mindjet:Priority2"
    PRIORITY_3 = "urn:mindjet:Priority3"
    FLAG = "urn:mindjet:Flag"
    STAR = "urn:mindjet:Star"
    TICK_GREEN = "urn:mindjet:TickGreen"
    TICK_YELLOW = "urn:mindjet:TickYellow"
    CROSS_RED = "urn:mindjet:CrossRed"


@dataclass
class Task:
    """Task metadata attached to a topic."""
    percentage: int = 0  # 0-100
    priority: TaskPriority = TaskPriority.NONE
    due_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    
    @property
    def status(self) -> TaskStatus:
        if self.percentage >= 100:
            return TaskStatus.COMPLETE
        elif self.percentage > 0:
            return TaskStatus.IN_PROGRESS
        return TaskStatus.NOT_STARTED


@dataclass
class Hyperlink:
    """A hyperlink attached to a topic."""
    url: str = ""
    text: str = ""


@dataclass  
class Note:
    """Rich text note attached to a topic."""
    plain_text: str = ""
    html: str = ""


@dataclass
class Topic:
    """A single topic node in a mind map.
    
    Topics form a tree structure via the `children` list.
    Each topic can have optional task metadata, icons, notes, and hyperlinks.
    """
    # Core
    oid: str = ""  # MindManager internal GUID
    text: str = ""
    
    # Tree structure
    children: list[Topic] = field(default_factory=list)
    parent: Optional[Topic] = field(default=None, repr=False)
    
    # Optional metadata
    task: Optional[Task] = None
    icons: list[IconMarker] = field(default_factory=list)
    hyperlinks: list[Hyperlink] = field(default_factory=list)
    note: Optional[Note] = None
    
    # Style (preserved for round-trip fidelity)
    _style_xml: Optional[str] = field(default=None, repr=False)
    # Raw XML element (for preserving unknown attributes)
    _raw_attribs: dict = field(default_factory=dict, repr=False)
    
    @property
    def depth(self) -> int:
        """Distance from root."""
        d = 0
        node = self.parent
        while node is not None:
            d += 1
            node = node.parent
        return d
    
    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0
    
    @property
    def path(self) -> list[str]:
        """List of topic texts from root to this node."""
        parts = []
        node = self
        while node is not None:
            parts.append(node.text)
            node = node.parent
        return list(reversed(parts))
    
    def find(self, text: str) -> Optional[Topic]:
        """Find first descendant with matching text (case-insensitive)."""
        text_lower = text.lower()
        if self.text.lower() == text_lower:
            return self
        for child in self.children:
            result = child.find(text)
            if result is not None:
                return result
        return None
    
    def find_all(self, text: str) -> list[Topic]:
        """Find all descendants with matching text (case-insensitive)."""
        results = []
        text_lower = text.lower()
        if self.text.lower() == text_lower:
            results.append(self)
        for child in self.children:
            results.extend(child.find_all(text))
        return results
    
    def walk(self):
        """Yield this topic and all descendants depth-first."""
        yield self
        for child in self.children:
            yield from child.walk()
    
    def add_child(self, text: str, **kwargs) -> Topic:
        """Create and append a new child topic."""
        child = Topic(text=text, parent=self, **kwargs)
        self.children.append(child)
        return child
    
    def remove(self) -> None:
        """Remove this topic from its parent's children list."""
        if self.parent is not None:
            self.parent.children = [c for c in self.parent.children if c is not self]
            self.parent = None
    
    def move_to(self, new_parent: Topic) -> None:
        """Move this topic to a new parent."""
        self.remove()
        self.parent = new_parent
        new_parent.children.append(self)
    
    def count(self) -> int:
        """Total number of descendants (including self)."""
        return sum(1 for _ in self.walk())
    
    def __str__(self) -> str:
        return self.text
    
    def __repr__(self) -> str:
        child_count = len(self.children)
        suffix = f" ({child_count} children)" if child_count else ""
        return f"Topic({self.text!r}{suffix})"


@dataclass
class MindMap:
    """A complete MindManager mind map.
    
    Contains the root topic (central topic) and map-level metadata.
    """
    root: Topic = field(default_factory=Topic)
    
    # Map metadata
    title: str = ""
    created: Optional[datetime] = None
    modified: Optional[datetime] = None
    
    # Preserved for round-trip fidelity
    _source_path: str = ""
    _xml_header: str = ""
    _xml_namespace: str = "http://schemas.mindjet.com/MindManager/Application/2003"
    
    @property
    def topic_count(self) -> int:
        return self.root.count()
    
    def find(self, text: str) -> Optional[Topic]:
        """Find first topic with matching text."""
        return self.root.find(text)
    
    def find_all(self, text: str) -> list[Topic]:
        """Find all topics with matching text."""
        return self.root.find_all(text)
    
    def walk(self):
        """Iterate all topics depth-first."""
        yield from self.root.walk()
    
    def tasks(self, status: Optional[TaskStatus] = None):
        """Yield all topics that have task metadata, optionally filtered by status."""
        for topic in self.walk():
            if topic.task is not None:
                if status is None or topic.task.status == status:
                    yield topic
    
    def __repr__(self) -> str:
        return f"MindMap({self.root.text!r}, {self.topic_count} topics)"
