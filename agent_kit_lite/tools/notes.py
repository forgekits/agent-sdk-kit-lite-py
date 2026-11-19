"""A small file-backed notes store, exposed to Claude as two tools.

It shows the pattern for a tool with side effects: a bounded input schema, a
store confined to one directory the operator chose, an accurate
``destructiveHint``, and an error path that tells Claude what went wrong.
Swap the JSONL file for your database when you embed the kit.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from claude_agent_sdk import ToolAnnotations, tool

MAX_BODY_CHARS = 20_000


@dataclass(frozen=True)
class Note:
    id: str
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: str


class NotesStore:
    """Append-only JSONL store. Fine for a demo and one process, not for concurrent writers."""

    def __init__(self, directory: str | Path) -> None:
        self.file = Path(directory).resolve() / "notes.jsonl"

    def all(self) -> list[Note]:
        if not self.file.exists():
            return []
        notes: list[Note] = []
        for line in self.file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                notes.append(
                    Note(
                        id=str(raw["id"]),
                        title=str(raw["title"]),
                        body=str(raw["body"]),
                        tags=tuple(str(t) for t in raw.get("tags", [])),
                        created_at=str(raw["created_at"]),
                    )
                )
            except (ValueError, KeyError, TypeError):
                continue  # a damaged line must not take the whole store down
        return notes

    def save(self, title: str, body: str, tags: list[str] | None = None) -> Note:
        if len(body) > MAX_BODY_CHARS:
            raise ValueError(f"Note body exceeds {MAX_BODY_CHARS} characters")
        note = Note(
            id=str(uuid.uuid4()),
            title=title.strip(),
            body=body,
            tags=tuple(t.strip().lower() for t in (tags or []) if t.strip()),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.file.parent.mkdir(parents=True, exist_ok=True)
        with self.file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(asdict(note)) + "\n")
        return note

    def search(self, query: str, limit: int = 10) -> list[Note]:
        q = query.strip().lower()
        notes = self.all()
        hits = [
            n
            for n in notes
            if not q or q in n.title.lower() or q in n.body.lower() or any(q in t for t in n.tags)
        ]
        return list(reversed(hits[-limit:]))  # newest first


def create_notes_tools(store: NotesStore) -> list[Any]:
    """Build the two note tools bound to a store."""

    async def save_note(args: dict[str, Any]) -> dict[str, Any]:
        try:
            note = store.save(str(args["title"]), str(args["body"]), list(args.get("tags") or []))
        except Exception as exc:  # noqa: BLE001 - the message is what Claude reads
            return {"content": [{"type": "text", "text": f"Could not save note: {exc}"}], "is_error": True}
        return {"content": [{"type": "text", "text": f'Saved note "{note.title}" (id {note.id}).'}]}

    async def search_notes(args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        limit = int(args.get("limit") or 10)
        try:
            notes = store.search(query, limit)
        except Exception as exc:  # noqa: BLE001
            return {"content": [{"type": "text", "text": f"Search failed: {exc}"}], "is_error": True}
        if not notes:
            return {"content": [{"type": "text", "text": f'No notes match "{query}".'}]}
        lines = []
        for n in notes:
            tags = f" ({', '.join(n.tags)})" if n.tags else ""
            lines.append(f"- [{n.created_at}] {n.title}{tags}\n  {n.body}")
        return {"content": [{"type": "text", "text": "\n".join(lines)}]}

    save_tool = tool(
        "save_note",
        "Save a note for later. Use it when the user asks you to remember something.",
        {
            "type": "object",
            "properties": {
                "title": {"type": "string", "minLength": 1, "maxLength": 200, "description": "Short title"},
                "body": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_BODY_CHARS,
                    "description": "The note text",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1, "maxLength": 40},
                    "maxItems": 10,
                    "description": "Optional tags",
                },
            },
            "required": ["title", "body"],
        },
        # Appending is a write, so destructiveHint is true. Not idempotent: calling twice saves twice.
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
        ),
    )(save_note)

    search_tool = tool(
        "search_notes",
        "Search saved notes by a word or phrase in title, body or tags. Returns newest first.",
        {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "maxLength": 200,
                    "description": "Search text; empty returns the newest notes",
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 50,
                    "description": "Max results, default 10",
                },
            },
            "required": ["query"],
        },
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True, openWorldHint=False),
    )(search_notes)

    return [save_tool, search_tool]
