"""Read MindManager .mmap files into Python objects."""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Union

from .models import (
    Hyperlink,
    IconMarker,
    MindMap,
    Note,
    Task,
    TaskPriority,
    Topic,
)

NS = "http://schemas.mindjet.com/MindManager/Application/2003"
_NS = f"{{{NS}}}"


def read(path: Union[str, Path]) -> MindMap:
    """Read a .mmap file and return a MindMap object.
    
    Args:
        path: Path to the .mmap file.
        
    Returns:
        A MindMap with the full topic tree.
        
    Raises:
        FileNotFoundError: If the file doesn't exist.
        zipfile.BadZipFile: If the file isn't a valid ZIP/mmap.
        ValueError: If Document.xml is missing or malformed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    # Extract Document.xml from the ZIP container
    with zipfile.ZipFile(path, "r") as zf:
        if "Document.xml" not in zf.namelist():
            raise ValueError(f"No Document.xml found in {path}")
        xml_bytes = zf.read("Document.xml")
    
    # Parse XML
    root_elem = ET.fromstring(xml_bytes)
    
    # Find the central topic
    one_topic = root_elem.find(f".//{_NS}OneTopic")
    if one_topic is None:
        raise ValueError("No OneTopic element found in Document.xml")
    
    topic_elem = one_topic.find(f"{_NS}Topic")
    if topic_elem is None:
        raise ValueError("No root Topic found under OneTopic")
    
    # Build the map
    mindmap = MindMap()
    mindmap._source_path = str(path)
    mindmap._xml_namespace = NS
    mindmap.root = _parse_topic(topic_elem, parent=None)
    mindmap.title = mindmap.root.text
    
    return mindmap


def _parse_topic(elem: ET.Element, parent: Topic | None) -> Topic:
    """Recursively parse a Topic XML element into a Topic object."""
    topic = Topic()
    topic.parent = parent
    
    # OId attribute
    topic.oid = elem.get("OId", "")
    
    # Preserve raw attributes for round-trip
    topic._raw_attribs = dict(elem.attrib)
    
    # Text
    text_elem = elem.find(f"{_NS}Text")
    if text_elem is not None:
        topic.text = text_elem.get("PlainText", "")
    
    # Task info
    task_elem = elem.find(f"{_NS}Task")
    if task_elem is not None:
        topic.task = _parse_task(task_elem)
    
    # Icon markers
    icons_elem = elem.find(f"{_NS}IconMarkers")
    if icons_elem is not None:
        for icon_elem in icons_elem:
            if icon_elem.tag == f"{_NS}IconMarker":
                marker = IconMarker(
                    icon_type=icon_elem.get("IconType", ""),
                    icon_signature=icon_elem.get("IconSignature", ""),
                )
                topic.icons.append(marker)
    
    # Hyperlinks
    hyperlinks_elem = elem.find(f"{_NS}Hyperlink")
    if hyperlinks_elem is not None:
        hl = Hyperlink(
            url=hyperlinks_elem.get("Url", ""),
            text=hyperlinks_elem.get("Text", ""),
        )
        topic.hyperlinks.append(hl)
    
    # Multiple hyperlinks via HyperlinkGroup
    hl_group = elem.find(f"{_NS}HyperlinkGroup")
    if hl_group is not None:
        for hl_elem in hl_group:
            if hl_elem.tag == f"{_NS}Hyperlink":
                hl = Hyperlink(
                    url=hl_elem.get("Url", ""),
                    text=hl_elem.get("Text", ""),
                )
                topic.hyperlinks.append(hl)
    
    # Notes
    notes_group = elem.find(f"{_NS}NotesGroup")
    if notes_group is not None:
        notes_elem = notes_group.find(f"{_NS}Notes")
        if notes_elem is not None:
            plain = notes_elem.get("PlainText", "")
            html_content = ""
            html_elem = notes_elem.find(f"{_NS}Html")
            if html_elem is not None and html_elem.text:
                html_content = html_elem.text
            topic.note = Note(plain_text=plain, html=html_content)
    
    # Style XML (preserve for round-trip)
    style_elem = elem.find(f"{_NS}SubTopicShape")
    if style_elem is not None:
        topic._style_xml = ET.tostring(style_elem, encoding="unicode")
    
    # Recurse into children
    subtopics_elem = elem.find(f"{_NS}SubTopics")
    if subtopics_elem is not None:
        for child_elem in subtopics_elem:
            if child_elem.tag == f"{_NS}Topic":
                child = _parse_topic(child_elem, parent=topic)
                topic.children.append(child)
    
    return topic


def _parse_task(elem: ET.Element) -> Task:
    """Parse a Task XML element."""
    task = Task()
    
    # Percentage
    pct = elem.get("TaskPercentage", "")
    if pct:
        try:
            task.percentage = int(float(pct))
        except ValueError:
            pass
    
    # Priority
    pri = elem.get("TaskPriority", "")
    try:
        task.priority = TaskPriority(pri)
    except ValueError:
        task.priority = TaskPriority.NONE
    
    # Due date
    due = elem.get("TaskDueDate", "")
    if due:
        task.due_date = _parse_date(due)
    
    # Start date
    start = elem.get("TaskStartDate", "")
    if start:
        task.start_date = _parse_date(start)
    
    return task


def _parse_date(date_str: str) -> datetime | None:
    """Parse MindManager date formats."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
