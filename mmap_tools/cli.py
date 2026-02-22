"""Command-line interface for mmap-tools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import read, write, to_markdown, from_markdown


def main():
    parser = argparse.ArgumentParser(
        prog="mmap-tools",
        description="Read, write, and convert MindManager .mmap files",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    
    # --- info ---
    p_info = sub.add_parser("info", help="Show map summary")
    p_info.add_argument("file", help="Path to .mmap file")
    p_info.add_argument("--depth", type=int, default=2, help="Tree depth to show (default: 2)")
    
    # --- tree ---
    p_tree = sub.add_parser("tree", help="Print full topic tree")
    p_tree.add_argument("file", help="Path to .mmap file")
    p_tree.add_argument("--depth", type=int, default=99, help="Max depth")
    p_tree.add_argument("--tasks-only", action="store_true", help="Only show topics with tasks")
    
    # --- export ---
    p_export = sub.add_parser("export", help="Export to markdown")
    p_export.add_argument("file", help="Path to .mmap file")
    p_export.add_argument("-o", "--output", help="Output markdown file (default: stdout)")
    
    # --- find ---
    p_find = sub.add_parser("find", help="Search for topics by text")
    p_find.add_argument("file", help="Path to .mmap file")
    p_find.add_argument("query", help="Text to search for")
    
    # --- tasks ---
    p_tasks = sub.add_parser("tasks", help="List all tasks")
    p_tasks.add_argument("file", help="Path to .mmap file")
    p_tasks.add_argument("--status", choices=["open", "done", "in-progress"], help="Filter by status")
    
    args = parser.parse_args()
    
    if args.command == "info":
        cmd_info(args)
    elif args.command == "tree":
        cmd_tree(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "find":
        cmd_find(args)
    elif args.command == "tasks":
        cmd_tasks(args)


def cmd_info(args):
    m = read(args.file)
    print(f"File: {args.file}")
    print(f"Title: {m.root.text}")
    print(f"Topics: {m.topic_count}")
    print(f"Tasks: {sum(1 for _ in m.tasks())}")
    print()
    
    def show(topic, depth=0, max_depth=2):
        if depth > max_depth:
            return
        child_count = len(topic.children)
        desc_count = topic.count() - 1
        suffix = f" ({desc_count} items)" if desc_count > 0 else ""
        task_mark = " ✓" if topic.task and topic.task.percentage >= 100 else ""
        task_mark = " ◔" if topic.task and 0 < topic.task.percentage < 100 else task_mark
        print("  " * depth + f"• {topic.text}{suffix}{task_mark}")
        for child in topic.children:
            show(child, depth + 1, max_depth)
    
    for child in m.root.children:
        show(child, 0, args.depth)


def cmd_tree(args):
    m = read(args.file)
    
    for topic in m.walk():
        if args.tasks_only and topic.task is None:
            continue
        indent = "  " * topic.depth
        task_info = ""
        if topic.task:
            t = topic.task
            parts = []
            if t.percentage >= 100:
                parts.append("✅")
            elif t.percentage > 0:
                parts.append(f"{t.percentage}%")
            if t.due_date:
                parts.append(f"📅 {t.due_date.strftime('%Y-%m-%d')}")
            if parts:
                task_info = f" [{' '.join(parts)}]"
        print(f"{indent}{topic.text}{task_info}")


def cmd_export(args):
    m = read(args.file)
    md = to_markdown(m)
    
    if args.output:
        Path(args.output).write_text(md, encoding="utf-8")
        print(f"Exported to {args.output}")
    else:
        print(md)


def cmd_find(args):
    m = read(args.file)
    query = args.query.lower()
    
    for topic in m.walk():
        if query in topic.text.lower():
            path = " → ".join(topic.path)
            task_info = ""
            if topic.task:
                task_info = f" [{topic.task.percentage}%]"
            print(f"{path}{task_info}")


def cmd_tasks(args):
    from .models import TaskStatus
    
    m = read(args.file)
    
    status_filter = None
    if args.status == "open":
        status_filter = TaskStatus.NOT_STARTED
    elif args.status == "done":
        status_filter = TaskStatus.COMPLETE
    elif args.status == "in-progress":
        status_filter = TaskStatus.IN_PROGRESS
    
    for topic in m.tasks(status=status_filter):
        t = topic.task
        status = "✅" if t.percentage >= 100 else f"{t.percentage}%"
        due = f" 📅 {t.due_date.strftime('%Y-%m-%d')}" if t.due_date else ""
        path = " → ".join(topic.path[-3:])  # Last 3 levels for readability
        print(f"[{status}] {path}{due}")


if __name__ == "__main__":
    main()
