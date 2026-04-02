#!/usr/bin/env python3
"""Terminal CLI for Manual Editor create/update/delete workflows.

Designed for automation and LLM usage:
- Accepts payload from --payload-json, --payload-file, or stdin
- Emits JSON responses to stdout
- Uses non-zero exit codes on failures
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ManualManagement import (
    create_manual_definition,
    delete_manual_definition,
    load_manual_editor_data,
    save_manual_definition,
)


def _read_payload(args: argparse.Namespace) -> dict:
    if args.payload_json:
        return json.loads(args.payload_json)

    if args.payload_file:
        payload_path = Path(args.payload_file)
        return json.loads(payload_path.read_text(encoding="utf-8"))

    if not sys.stdin.isatty():
        return json.load(sys.stdin)

    raise ValueError("Payload is required. Use --payload-json, --payload-file, or pipe JSON via stdin.")


def _dump_success(data: dict) -> int:
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def _dump_error(message: str, exit_code: int = 1) -> int:
    print(json.dumps({"success": False, "error": message}, ensure_ascii=False), file=sys.stderr)
    return exit_code


def _command_create(args: argparse.Namespace) -> int:
    payload = _read_payload(args)
    manual = create_manual_definition(payload, scope=args.scope, module=args.module)
    return _dump_success({"success": True, "action": "create", "manual": manual})


def _command_update(args: argparse.Namespace) -> int:
    payload = _read_payload(args)
    manual_id = args.manual_id or payload.get("manual_id")
    if not manual_id:
        raise ValueError("manual_id is required for update (flag or payload field).")

    manual = save_manual_definition(manual_id, payload, scope=args.scope, module=args.module)
    return _dump_success({"success": True, "action": "update", "manual": manual})


def _command_upsert(args: argparse.Namespace) -> int:
    payload = _read_payload(args)
    manual_id = payload.get("manual_id")
    if not manual_id:
        raise ValueError("manual_id is required in payload for upsert.")

    try:
        manual = create_manual_definition(payload, scope=args.scope, module=args.module)
        action = "create"
    except ValueError as exc:
        if "already exists" not in str(exc).lower():
            raise
        manual = save_manual_definition(manual_id, payload, scope=args.scope, module=args.module)
        action = "update"

    return _dump_success({"success": True, "action": action, "manual": manual})


def _command_delete(args: argparse.Namespace) -> int:
    delete_manual_definition(args.manual_id, scope=args.scope, module=args.module)
    return _dump_success({"success": True, "action": "delete", "manual_id": args.manual_id})


def _command_list(args: argparse.Namespace) -> int:
    data = load_manual_editor_data(scope=args.scope, module=args.module)
    manuals = data.get("manuals", [])
    slim = [
        {
            "manual_id": row.get("manual_id"),
            "title": row.get("title"),
            "module": row.get("module"),
            "source_folder": row.get("source_folder"),
            "sort_order": row.get("sort_order"),
        }
        for row in manuals
    ]
    return _dump_success({
        "success": True,
        "action": "list",
        "count": len(slim),
        "manuals": slim,
    })


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manual Editor automation CLI")
    parser.add_argument("--scope", default="manuals", choices=["manuals", "updates"], help="Editor scope")
    parser.add_argument(
        "--module",
        default="common",
        choices=["common", "v1", "v2", "colony", "currency"],
        help="Target module",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("create", "update", "upsert"):
        cmd = subparsers.add_parser(command, help=f"{command.title()} a manual from JSON payload")
        cmd.add_argument("--payload-file", help="Path to JSON payload file")
        cmd.add_argument("--payload-json", help="Raw JSON payload string")
        if command == "update":
            cmd.add_argument("--manual-id", help="Manual ID override")

    cmd_delete = subparsers.add_parser("delete", help="Delete a manual by id")
    cmd_delete.add_argument("manual_id", help="Manual ID to delete")

    subparsers.add_parser("list", help="List manuals in the selected scope/module")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "create": _command_create,
        "update": _command_update,
        "upsert": _command_upsert,
        "delete": _command_delete,
        "list": _command_list,
    }

    try:
        return handlers[args.command](args)
    except json.JSONDecodeError as exc:
        return _dump_error(f"Invalid JSON payload: {exc}", exit_code=2)
    except FileNotFoundError as exc:
        return _dump_error(f"File not found: {exc}", exit_code=2)
    except ValueError as exc:
        return _dump_error(str(exc), exit_code=2)
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        return _dump_error(f"Unexpected error: {exc}", exit_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
