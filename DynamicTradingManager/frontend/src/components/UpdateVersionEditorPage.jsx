import React, { useState, useEffect } from 'react';
import { Alert, Box, Button, Paper, Stack, Typography } from '@mui/material';
import ManualEditorPage from './ManualEditorPage';
import GitAiAssistant from './Common/GitAiAssistant';
import { createManualDefinition, getManualEditorData, saveManualDefinition, getWorkshopTargets } from '../services/api';

const getTodayDateString = () => {
	return new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
};

const defaultPrompt = `Task:
Generate ONLY valid JSON (no markdown fences, no extra text) for a Project Zomboid What's New manual.

Return this exact shape:
{
  "manual_id": "dt_update_YYYY_MM_DD",
  "module": "common|v1|v2|colony|currency",
  "title": "${getTodayDateString()} Update",
  "description": "max 69 chars",
  "release_version": "x.y.z",
  "popup_version": "x.y.z",
  "auto_open_on_update": true,
  "sort_order": 10,
  "chapters": [
    {
      "id": "release_notes",
      "title": "Release Notes",
      "description": "What changed"
    }
  ],
  "pages": [
    {
      "id": "overview",
      "chapter_id": "release_notes",
      "title": "Overview",
      "keywords": ["update", "release"],
      "blocks": [
        { "type": "heading", "id": "highlights", "level": 1, "text": "Highlights" },
        { "type": "bullet_list", "items": ["item 1", "item 2"] },
        { "type": "callout", "tone": "info", "title": "Note", "text": "optional" }
      ]
    }
  ]
}

Rules:
- Keep output strict JSON.
- The "title" field MUST follow the format "${getTodayDateString()} Update".
- The "title" field MUST NOT exceed 22 characters. If the full month name makes the title exceed 22 characters, abbreviate the month (e.g., "Sept" instead of "September").
- The "description" field MUST NOT exceed 69 characters.
- Use only manual editor block types: heading, paragraph, bullet_list, callout, image.
- Prefer concise gameplay-impact bullets.`;

const slugify = (value) => String(value || '')
	.trim()
	.toLowerCase()
	.replace(/[^a-z0-9_-]+/g, '_')
	.replace(/_+/g, '_')
	.replace(/^_+|_+$/g, '');

const getTodayUpdateId = () => {
	const today = new Date().toISOString().slice(0, 10).replace(/-/g, '_');
	return `dt_update_${today}`;
};

const extractJsonPayload = (text) => {
	const raw = String(text || '').trim();
	if (!raw) {
		throw new Error('No JSON text found.');
	}

	const fenced = raw.match(/```json\s*([\s\S]*?)```/i) || raw.match(/```\s*([\s\S]*?)```/i);
	const candidate = fenced ? fenced[1].trim() : raw;
	return JSON.parse(candidate);
};

const normalizeBlock = (block, index) => {
	if (typeof block === 'string') {
		return { type: 'paragraph', text: block };
	}

	const type = String(block?.type || '').trim();
	if (type === 'heading') {
		return {
			type: 'heading',
			id: slugify(block.id || `heading_${index + 1}`),
			level: Number(block.level || 1),
			text: String(block.text || ''),
		};
	}

	if (type === 'bullet_list') {
		return {
			type: 'bullet_list',
			items: Array.isArray(block.items) ? block.items.map((item) => String(item)) : [],
		};
	}

	if (type === 'callout') {
		return {
			type: 'callout',
			tone: String(block.tone || 'info'),
			title: String(block.title || ''),
			text: String(block.text || ''),
		};
	}

	if (type === 'image') {
		return {
			type: 'image',
			path: String(block.path || ''),
			caption: String(block.caption || ''),
			width: Number(block.width || 220),
			height: Number(block.height || 140),
		};
	}

	return {
		type: 'paragraph',
		text: String(block?.text || ''),
	};
};

const buildManualPayload = (input) => {
	const payload = input?.manual ? input.manual : input;
	const module = ['common', 'v1', 'v2', 'colony', 'currency'].includes(payload.module)
		? payload.module
		: 'common';
	const manualId = slugify(payload.manual_id || getTodayUpdateId());

	const chapters = Array.isArray(payload.chapters) && payload.chapters.length > 0
		? payload.chapters.map((chapter, index) => ({
			id: slugify(chapter.id || `release_notes_${index + 1}`),
			title: String(chapter.title || `Release Notes ${index + 1}`),
			description: String(chapter.description || 'What changed in this update.').slice(0, 69),
		}))
		: [{ id: 'release_notes', title: 'Release Notes', description: 'What changed in this update.' }];

	const firstChapterId = chapters[0].id;
	const pagesInput = Array.isArray(payload.pages) ? payload.pages : [];
	const pages = pagesInput.length > 0
		? pagesInput.map((page, index) => ({
			id: slugify(page.id || `overview_${index + 1}`),
			chapter_id: slugify(page.chapter_id || page.chapterId || firstChapterId) || firstChapterId,
			title: String(page.title || `Overview ${index + 1}`),
			keywords: Array.isArray(page.keywords) ? page.keywords.map((keyword) => String(keyword)) : ['update', 'release'],
			blocks: Array.isArray(page.blocks)
				? page.blocks.map((block, blockIndex) => normalizeBlock(block, blockIndex))
				: [{ type: 'paragraph', text: String(page.text || '') }],
		}))
		: [{
			id: 'overview',
			chapter_id: firstChapterId,
			title: 'Overview',
			keywords: ['update', 'release'],
			blocks: [{ type: 'paragraph', text: String(payload.summary || 'Update details.') }],
		}];

	return {
		module,
		manual: {
			manual_id: manualId,
			title: String(payload.title || 'Update'),
			description: String(payload.description || 'Latest update notes.').slice(0, 69),
			start_page_id: pages[0]?.id || '',
			audiences: [module],
			sort_order: Number(payload.sort_order || 10),
			release_version: String(payload.release_version || ''),
			popup_version: String(payload.popup_version || payload.release_version || ''),
			auto_open_on_update: payload.auto_open_on_update !== false,
			is_whats_new: true,
			manual_type: 'whats_new',
			show_in_library: false,
			source_folder: 'WhatsNew',
			chapters,
			pages,
		},
	};
};

const UpdateVersionEditorPage = () => {
	const [generatedText, setGeneratedText] = useState('');
	const [status, setStatus] = useState({ type: '', message: '' });
	const [editorReloadToken, setEditorReloadToken] = useState(0);
	const [latestCommitHash, setLatestCommitHash] = useState('');
	const [targets, setTargets] = useState([]);
	const [selectedTarget, setSelectedTarget] = useState('dynamictrading');

	useEffect(() => {
		getWorkshopTargets().then(res => {
			setTargets(res.data?.targets || []);
			if (res.data?.default_target) setSelectedTarget(res.data.default_target);
			else if (res.data?.targets?.length > 0) setSelectedTarget(res.data.targets[0].key);
		}).catch(() => {});
	}, []);

	const applyJsonAsUpdatePage = async () => {
		try {
			setStatus({ type: '', message: '' });
			const parsed = extractJsonPayload(generatedText);
			const { module, manual } = buildManualPayload(parsed);

			const existing = await getManualEditorData('updates', module);
			const alreadyExists = (existing.data?.manuals || []).some((item) => item.manual_id === manual.manual_id);

			if (alreadyExists) {
				await saveManualDefinition(manual.manual_id, manual, 'updates', module);
				setStatus({ type: 'success', message: `Updated What's New page ${manual.manual_id} (${module}).` });
			} else {
				await createManualDefinition(manual, 'updates', module);
				setStatus({ type: 'success', message: `Created What's New page ${manual.manual_id} (${module}).` });
			}
			
			if (latestCommitHash) {
				localStorage.setItem('dt_update_system_prompt_last_hash', latestCommitHash);
			}
			
			setEditorReloadToken((current) => current + 1);
		} catch (error) {
			setStatus({
				type: 'error',
				message: error?.response?.data?.detail || error?.message || 'Failed to apply JSON output.',
			});
		}
	};

	return (
		<Stack spacing={2}>
			<GitAiAssistant
				title="Update Helper (Git + Puter)"
				helperText="Generate strict JSON and auto-build a What's New page from the output."
				outputValue={generatedText}
				onOutputChange={setGeneratedText}
				storageKey="dt_update_system_prompt"
				defaultPrompt={defaultPrompt}
				onLatestHash={setLatestCommitHash}
				availableTargets={targets}
				selectedTarget={selectedTarget}
				onTargetChange={setSelectedTarget}
				showSuiteToggle={true}
			/>

			<Paper sx={{ p: 2 }}>
				<Stack spacing={1.5}>
					<Typography variant="h6">JSON Import To What's New</Typography>
					<Typography variant="body2" color="text.secondary">
						Paste AI JSON output above, then click apply to auto-create or update the What's New manual entry.
					</Typography>
					<Stack direction="row" spacing={1}>
						<Button variant="contained" onClick={applyJsonAsUpdatePage}>
							Apply JSON To What's New
						</Button>
					</Stack>
					{status.message && <Alert severity={status.type || 'info'}>{status.message}</Alert>}
				</Stack>
			</Paper>

			<Box>
				<ManualEditorPage key={editorReloadToken} editorScope="updates" />
			</Box>
		</Stack>
	);
};

export default UpdateVersionEditorPage;
