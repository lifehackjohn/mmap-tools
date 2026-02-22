"""Write MindMap objects back to .mmap files.

Key principle: preserve ALL existing XML data that we don't explicitly model.
This ensures round-trip fidelity — open in MindManager, save, our output is identical
minus the changes we intended.
"""

from __future__ import annotations

import shutil
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from io import BytesIO
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


def write(mindmap: MindMap, path: Union[str, Path], *, backup: bool = True) -> Path:
    """Write a MindMap to a .mmap file.
    
    If the source .mmap exists, this performs a surgical update:
    reads the original ZIP, modifies Document.xml, writes a new ZIP.
    
    If no source exists (new map), creates a minimal .mmap from scratch.
    
    Args:
        mindmap: The MindMap to write.
        path: Output path for the .mmap file.
        backup: If True and path exists, create a .mmap.bak before overwriting.
        
    Returns:
        The path written to.
    """
    path = Path(path)
    source = Path(mindmap._source_path) if mindmap._source_path else None
    
    if source and source.exists():
        return _update_existing(mindmap, source, path, backup=backup)
    else:
        return _create_new(mindmap, path)


def _update_existing(
    mindmap: MindMap, source: Path, dest: Path, *, backup: bool = True
) -> Path:
    """Update an existing .mmap by modifying only Document.xml."""
    
    # Backup
    if backup and dest.exists():
        bak = dest.with_suffix(".mmap.bak")
        shutil.copy2(dest, bak)
    
    # Read original ZIP contents
    original_files = {}
    with zipfile.ZipFile(source, "r") as zf:
        for name in zf.namelist():
            original_files[name] = zf.read(name)
    
    # Parse and update Document.xml
    doc_xml = original_files["Document.xml"]
    root_elem = ET.fromstring(doc_xml)
    
    # Register namespace to avoid ns0: prefixes
    ET.register_namespace("", NS)
    
    # Find the OneTopic and rebuild the topic tree
    one_topic = root_elem.find(f".//{_NS}OneTopic")
    if one_topic is None:
        raise ValueError("No OneTopic in source Document.xml")
    
    # Remove existing topic
    old_topic = one_topic.find(f"{_NS}Topic")
    if old_topic is not None:
        one_topic.remove(old_topic)
    
    # Build new topic tree
    new_topic_elem = _build_topic_elem(mindmap.root)
    one_topic.append(new_topic_elem)
    
    # Serialize updated XML
    updated_xml = ET.tostring(root_elem, encoding="unicode", xml_declaration=True)
    original_files["Document.xml"] = updated_xml.encode("utf-8")
    
    # Write new ZIP
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in original_files.items():
            zf.writestr(name, data)
    
    dest.write_bytes(buf.getvalue())
    return dest


def _create_new(mindmap: MindMap, path: Path) -> Path:
    """Create a new .mmap file from scratch."""
    
    ET.register_namespace("", NS)
    
    # Build minimal Document.xml
    root_elem = ET.Element(f"{_NS}Map")
    
    one_topic = ET.SubElement(root_elem, f"{_NS}OneTopic")
    topic_elem = _build_topic_elem(mindmap.root)
    one_topic.append(topic_elem)
    
    xml_str = ET.tostring(root_elem, encoding="unicode", xml_declaration=True)
    
    # Write ZIP
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Document.xml", xml_str.encode("utf-8"))
    
    path.write_bytes(buf.getvalue())
    return path


def _build_topic_elem(topic: Topic) -> ET.Element:
    """Build an XML Element from a Topic, recursively."""
    elem = ET.Element(f"{_NS}Topic")
    
    # OId
    oid = topic.oid or str(uuid.uuid4()).upper()
    elem.set("OId", oid)
    
    # Restore any raw attributes we preserved
    for key, val in topic._raw_attribs.items():
        if key != "OId":  # Don't duplicate
            elem.set(key, val)
    
    # Text
    if topic.text:
        text_elem = ET.SubElement(elem, f"{_NS}Text")
        text_elem.set("PlainText", topic.text)
    
    # Task
    if topic.task is not None:
        _build_task_elem(elem, topic.task)
    
    # Icon markers
    if topic.icons:
        icons_elem = ET.SubElement(elem, f"{_NS}IconMarkers")
        for icon in topic.icons:
            icon_elem = ET.SubElement(icons_elem, f"{_NS}IconMarker")
            if icon.icon_type:
                icon_elem.set("IconType", icon.icon_type)
            if icon.icon_signature:
                icon_elem.set("IconSignature", icon.icon_signature)
    
    # Hyperlinks
    if len(topic.hyperlinks) == 1:
        hl = topic.hyperlinks[0]
        hl_elem = ET.SubElement(elem, f"{_NS}Hyperlink")
        hl_elem.set("Url", hl.url)
        if hl.text:
            hl_elem.set("Text", hl.text)
    elif len(topic.hyperlinks) > 1:
        hl_group = ET.SubElement(elem, f"{_NS}HyperlinkGroup")
        for hl in topic.hyperlinks:
            hl_elem = ET.SubElement(hl_group, f"{_NS}Hyperlink")
            hl_elem.set("Url", hl.url)
            if hl.text:
                hl_elem.set("Text", hl.text)
    
    # Notes
    if topic.note:
        notes_group = ET.SubElement(elem, f"{_NS}NotesGroup")
        notes_elem = ET.SubElement(notes_group, f"{_NS}Notes")
        notes_elem.set("PlainText", topic.note.plain_text)
        if topic.note.html:
            html_elem = ET.SubElement(notes_elem, f"{_NS}Html")
            html_elem.text = topic.note.html
    
    # Children
    if topic.children:
        subtopics_elem = ET.SubElement(elem, f"{_NS}SubTopics")
        for child in topic.children:
            child_elem = _build_topic_elem(child)
            subtopics_elem.append(child_elem)
    
    return elem


def _build_task_elem(parent: ET.Element, task: Task) -> None:
    """Add a Task element to a topic element."""
    task_elem = ET.SubElement(parent, f"{_NS}Task")
    
    if task.percentage > 0:
        task_elem.set("TaskPercentage", str(task.percentage))
    
    if task.priority != TaskPriority.NONE:
        task_elem.set("TaskPriority", task.priority.value)
    
    if task.due_date:
        task_elem.set("TaskDueDate", task.due_date.strftime("%Y-%m-%dT%H:%M:%S"))
    
    if task.start_date:
        task_elem.set("TaskStartDate", task.start_date.strftime("%Y-%m-%dT%H:%M:%S"))
