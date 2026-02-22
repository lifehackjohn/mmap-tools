"""Core tests for mmap-tools."""

import tempfile
from pathlib import Path

import mmap_tools
from mmap_tools import MindMap, Topic, Task, TaskPriority, TaskStatus


def test_create_empty_map():
    m = MindMap()
    m.root.text = "Test Map"
    assert m.topic_count == 1
    assert m.root.text == "Test Map"


def test_add_children():
    m = MindMap()
    m.root.text = "Root"
    child1 = m.root.add_child("Child 1")
    child2 = m.root.add_child("Child 2")
    grandchild = child1.add_child("Grandchild")
    
    assert m.topic_count == 4
    assert len(m.root.children) == 2
    assert grandchild.depth == 2
    assert grandchild.path == ["Root", "Child 1", "Grandchild"]


def test_find():
    m = MindMap()
    m.root.text = "Root"
    m.root.add_child("Alpha")
    m.root.add_child("Beta")
    m.root.children[0].add_child("Gamma")
    
    assert m.find("Beta") is not None
    assert m.find("beta").text == "Beta"  # case-insensitive
    assert m.find("Gamma").depth == 2
    assert m.find("nonexistent") is None


def test_task_status():
    t = Task(percentage=0)
    assert t.status == TaskStatus.NOT_STARTED
    
    t.percentage = 50
    assert t.status == TaskStatus.IN_PROGRESS
    
    t.percentage = 100
    assert t.status == TaskStatus.COMPLETE


def test_task_priority():
    t = Task(priority=TaskPriority.HIGH)
    assert t.priority == TaskPriority.HIGH
    assert t.priority.value == "1"


def test_walk():
    m = MindMap()
    m.root.text = "Root"
    m.root.add_child("A").add_child("A1")
    m.root.add_child("B")
    
    names = [t.text for t in m.walk()]
    assert names == ["Root", "A", "A1", "B"]


def test_remove_and_move():
    m = MindMap()
    m.root.text = "Root"
    a = m.root.add_child("A")
    b = m.root.add_child("B")
    c = a.add_child("C")
    
    # Move C from A to B
    c.move_to(b)
    assert len(a.children) == 0
    assert len(b.children) == 1
    assert b.children[0].text == "C"


def test_tasks_filter():
    m = MindMap()
    m.root.text = "Root"
    
    open_task = m.root.add_child("Open")
    open_task.task = Task(percentage=0)
    
    done_task = m.root.add_child("Done")
    done_task.task = Task(percentage=100)
    
    no_task = m.root.add_child("No task")
    
    all_tasks = list(m.tasks())
    assert len(all_tasks) == 2
    
    open_tasks = list(m.tasks(status=TaskStatus.NOT_STARTED))
    assert len(open_tasks) == 1
    assert open_tasks[0].text == "Open"


def test_write_and_read_roundtrip():
    """Create a map, write it, read it back, verify."""
    m = MindMap()
    m.root.text = "Test Roundtrip"
    
    child = m.root.add_child("Task Item")
    child.task = Task(percentage=50, priority=TaskPriority.HIGH)
    
    m.root.add_child("Plain Item")
    m.root.children[0].add_child("Nested")
    
    with tempfile.NamedTemporaryFile(suffix=".mmap", delete=False) as f:
        path = Path(f.name)
    
    try:
        mmap_tools.write(m, path)
        
        m2 = mmap_tools.read(path)
        assert m2.root.text == "Test Roundtrip"
        assert m2.topic_count == 4
        assert m2.find("Task Item").task.percentage == 50
        assert m2.find("Task Item").task.priority == TaskPriority.HIGH
        assert m2.find("Nested") is not None
    finally:
        path.unlink(missing_ok=True)


def test_markdown_export():
    m = MindMap()
    m.root.text = "My Tasks"
    
    branch = m.root.add_child("Work")
    task = branch.add_child("Review PR")
    task.task = Task(percentage=0, priority=TaskPriority.HIGH)
    
    done = branch.add_child("Ship feature")
    done.task = Task(percentage=100)
    
    md = mmap_tools.to_markdown(m, include_frontmatter=False)
    
    assert "# My Tasks" in md
    assert "## Work" in md
    assert "- [ ] Review PR ⏫" in md
    assert "- [x] Ship feature" in md


def test_markdown_roundtrip():
    m = MindMap()
    m.root.text = "Roundtrip"
    branch = m.root.add_child("Category")
    t = branch.add_child("Do thing")
    t.task = Task(percentage=0, priority=TaskPriority.MEDIUM)
    
    md = mmap_tools.to_markdown(m)
    m2 = mmap_tools.from_markdown(md)
    
    assert m2.root.text == "Roundtrip"
    assert m2.find("Do thing") is not None
    assert m2.find("Do thing").task is not None
    assert m2.find("Do thing").task.priority == TaskPriority.MEDIUM
