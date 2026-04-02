# Manual Editor CLI

This CLI exposes Manual Editor create/update/delete/list operations for terminal automation and LLM workflows.

## Run

From `DynamicTradingManager/backend`:

```bash
python manual_editor_cli.py --help
```

From project root:

```bash
python backend/manual_editor_cli.py --help
```

Recommended wrapper (auto-uses project venv):

```bash
./manual_editor_cli.sh --help
```

## Commands

- `list`: list manuals for module/scope
- `create`: create from JSON payload
- `update`: update existing manual from JSON payload
- `upsert`: create or update from JSON payload
- `delete`: delete by manual id

Common flags:

- `--scope manuals|updates` (default: `manuals`)
- `--module common|v1|v2|colony|currency` (default: `common`)

Payload input (for `create`, `update`, `upsert`):

- `--payload-file /path/payload.json`
- `--payload-json '{...}'`
- or pipe JSON via stdin

## Examples

List manuals:

```bash
python manual_editor_cli.py --scope manuals --module common list
```

Upsert from file:

```bash
./manual_editor_cli.sh --scope manuals --module common upsert --payload-file ./payload.json
```

Upsert from stdin:

```bash
cat payload.json | ./manual_editor_cli.sh --scope manuals --module common upsert
```

Delete manual:

```bash
./manual_editor_cli.sh --scope manuals --module common delete manual_new
```

## Minimal payload template

```json
{
	"manual_id": "manual_new",
	"title": "Manual Title",
	"description": "Short description up to 69 chars",
	"start_page_id": "intro",
	"audiences": ["common"],
	"sort_order": 300000,
	"source_folder": "Universal",
	"chapters": [
		{
			"id": "getting_started",
			"title": "Getting Started",
			"description": "Chapter summary"
		}
	],
	"pages": [
		{
			"id": "intro",
			"chapter_id": "getting_started",
			"title": "Introduction",
			"keywords": ["intro"],
			"blocks": [
				{
					"type": "paragraph",
					"text": "Welcome to the manual."
				}
			]
		}
	]
}
```

## LLM-friendly behavior

- Success output is JSON to stdout
- Errors are JSON to stderr with non-zero exit code
- Reuses the same backend ManualManagement normalization and validation rules
