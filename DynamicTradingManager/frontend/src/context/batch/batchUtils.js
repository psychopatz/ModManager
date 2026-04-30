// Pure utility functions and constants — no React, no API calls.

export const slugify = (str) =>
    str.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');

export const STAGE2_CATEGORIES = ['Features', 'Fixes', 'QoL', 'Performance', 'Balance', 'Misc'];
export const CACHE_PREFIX = 'git_batch_cache_';

export const safeJsonParse = (raw, fallback = null) => {
    if (!raw) return fallback;
    try { return JSON.parse(raw); } catch { return fallback; }
};

export const extractSection = (text, header) => {
    if (!text) return '';
    const blockRe = new RegExp(`\\[${header}\\][^\\S\\n]*\\n([\\s\\S]*?)(?=\\n\\[[A-Z_]+\\]|$)`, 'i');
    const bm = text.match(blockRe);
    if (bm) return bm[1].trim();
    const inlineRe = new RegExp(`\\[${header}\\][:\\s]+(.+)`, 'i');
    const im = text.match(inlineRe);
    return im ? im[1].trim() : '';
};

export const SECTION_TAG_RE = /\[(TITLE|IMPACT|TAGS|EXPLANATION|COMMIT_REFS)\][:\s]*/gi;

export const stripLLMArtifacts = (text) => {
    let clean = String(text || '');

    // Remove fenced code wrappers if the model encloses output in markdown blocks.
    clean = clean.replace(/```(?:markdown|md|text|json)?\s*/gi, '').replace(/```/g, '');

    // Remove common hidden reasoning tags leaked by some models.
    clean = clean.replace(/<think>[\s\S]*?<\/think>/gi, '');
    clean = clean.replace(/<analysis>[\s\S]*?<\/analysis>/gi, '');

    // Remove standalone pseudo-tags that should never be user-facing content.
    clean = clean
        .split('\n')
        .filter((line) => !/^\s*<\/?(think|analysis)\s*>\s*$/i.test(line))
        .join('\n');

    return clean.trim();
};

export const sanitizePageText = (text) =>
    stripLLMArtifacts(text).replace(SECTION_TAG_RE, '').replace(/\n{3,}/g, '\n\n').trim();

export const parseStage1StructuredItem = (text, fallback) => {
    const clean = stripLLMArtifacts(text);
    const titleFromTag = extractSection(clean, 'TITLE').split('\n')[0]?.trim() || '';
    const impactFromTag = extractSection(clean, 'IMPACT').split('\n')[0]?.trim() || '';
    const tagsRaw = extractSection(clean, 'TAGS').split('\n')[0] || '';
    const explanationRaw = extractSection(clean, 'EXPLANATION');
    const explanation = explanationRaw ? sanitizePageText(explanationRaw) : sanitizePageText(clean);
    const refsSection = extractSection(clean, 'COMMIT_REFS');

    const commitRefs = refsSection
        ? refsSection.split('\n').map((l) => l.replace(/^[-*]\s*/, '').trim()).filter(Boolean)
        : (fallback.commitRefs || []);

    const tags = tagsRaw
        ? tagsRaw.split(',').map((t) => t.trim()).filter(Boolean)
        : (fallback.tags || []);

    const item = {
        id: fallback.id,
        date: fallback.date,
        sourceRepos: fallback.sourceRepos,
        title: titleFromTag || fallback.title,
        explanation: explanation || fallback.explanation,
        impact: impactFromTag || fallback.impact,
        tags,
        commitRefs,
        parseWarnings: [],
    };

    if (!titleFromTag) item.parseWarnings.push('Missing [TITLE], fallback used.');
    if (!impactFromTag) item.parseWarnings.push('Missing [IMPACT], fallback used.');
    if (!extractSection(clean, 'EXPLANATION')) item.parseWarnings.push('Missing [EXPLANATION], full response used.');
    if (!refsSection) item.parseWarnings.push('Missing [COMMIT_REFS], fallback used.');

    return item;
};

export const categoryFromLabel = (label = '') => {
    const normalized = label.trim().toLowerCase();
    const hit = STAGE2_CATEGORIES.find((c) => c.toLowerCase() === normalized);
    return hit || 'Misc';
};

export const parseStage2Categorization = (content, items) => {
    const lines = (content || '').split('\n').map((l) => l.trim()).filter(Boolean);
    const map = {};
    const summaries = {};
    STAGE2_CATEGORIES.forEach((c) => { summaries[c] = ''; });

    let overallTitle = 'Update Summary';
    let inMap = false;
    let inSummaries = false;

    for (const line of lines) {
        if (/^OVERALL_TITLE\s*:/i.test(line)) {
            overallTitle = line.replace(/^OVERALL_TITLE\s*:/i, '').trim() || overallTitle;
            continue;
        }
        if (/^CATEGORY_MAP\s*:/i.test(line)) { inMap = true; inSummaries = false; continue; }
        if (/^CATEGORY_SUMMARIES\s*:/i.test(line)) { inMap = false; inSummaries = true; continue; }
        if (inMap) {
            const m = line.match(/^[-*]\s*(.*?)\s*=>\s*(.+)$/);
            if (m) map[m[1].trim()] = categoryFromLabel(m[2].trim());
            continue;
        }
        if (inSummaries) {
            const m = line.match(/^([A-Za-z]+)\s*:\s*(.*)$/);
            if (m) summaries[categoryFromLabel(m[1])] = m[2].trim();
        }
    }

    items.forEach((item) => { if (!map[item.id]) map[item.id] = 'Misc'; });
    return { overallTitle, map, summaries };
};

export const normalizeOverallTitle = (title, categorization, stage1Items) => {
    const clean = (title || '').trim();
    const looksDateOnly =
        /^(daily|weekly|monthly)?\s*(update|update log|changelog|release notes)?\s*\(?[a-z]*\s*\d{1,2}(?:\s*[-–]\s*\d{1,2})?,?\s*\d{4}\)?$/i.test(clean) ||
        /^\d{4}-\d{2}-\d{2}(\s*[-–]\s*\d{4}-\d{2}-\d{2})?$/i.test(clean) ||
        clean.length < 8;

    if (!looksDateOnly) return clean;

    const categoryCounts = STAGE2_CATEGORIES
        .map((category) => ({
            category,
            count: stage1Items.filter((item) => categorization.map[item.id] === category).length,
        }))
        .filter((row) => row.count > 0 && row.category !== 'Misc')
        .sort((a, b) => b.count - a.count);

    if (categoryCounts.length === 0) return 'Mod Update Roundup';
    if (categoryCounts.length === 1) return `${categoryCounts[0].category} Spotlight Update`;
    return `${categoryCounts[0].category} and ${categoryCounts[1].category} Update Roundup`;
};

export const generateSteamBBCode = (title, categorization, pages) => {
    const releaseDate = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const lines = [];
    lines.push(`[h1]${title}[/h1]`);
    lines.push(`[i]Released ${releaseDate}[/i]`);
    lines.push('[hr][/hr]');
    lines.push('');
    lines.push("Thank you for your continued support! Here's a full breakdown of what changed in this update:");
    lines.push('');

    const icons = { Features: '🚀', Fixes: '🔧', QoL: '✨', Performance: '⚡', Balance: '⚖️', Misc: '📝' };
    STAGE2_CATEGORIES.forEach((cat) => {
        const catPage = pages.find((p) => p.title === cat);
        if (!catPage) return;
        const summary = categorization.summaries?.[cat];
        const headings = catPage.blocks.filter((b) => b.type === 'heading' && b.level === 2);
        if (headings.length === 0) return;

        lines.push(`[h2]${icons[cat] || '▸'} ${cat}[/h2]`);
        if (summary) lines.push(`[i]${summary}[/i]`);
        lines.push('');
        lines.push('[list]');
        headings.forEach((h) => {
            const hIdx = catPage.blocks.indexOf(h);
            const impact = catPage.blocks.slice(hIdx + 1, hIdx + 4).find((b) => b.type === 'callout' && b.tone === 'success');
            lines.push(impact ? `[*][b]${h.text}[/b] — ${impact.text}` : `[*][b]${h.text}[/b]`);
        });
        lines.push('[/list]');
        lines.push('');
    });

    lines.push('[hr][/hr]');
    lines.push('[i]If you enjoy this mod, please consider leaving a rating and sharing it with your friends![/i]');
    return lines.join('\n');
};

export const assembleCategoryPages = (stage1Items, categorization) => {
    return STAGE2_CATEGORIES.map((category) => {
        const items = stage1Items.filter((item) => categorization.map[item.id] === category);
        if (items.length === 0) return null;

        const blocks = [];
        if (categorization.summaries?.[category]) {
            blocks.push({ type: 'callout', tone: 'info', title: `${category} Highlights`, text: categorization.summaries[category] });
        }
        items.forEach((item) => {
            blocks.push({ type: 'heading', id: `item_${slugify(item.id || item.title || 'entry')}`, level: 2, text: item.title });
            const cleanExplanation = sanitizePageText(item.explanation);
            if (cleanExplanation) blocks.push({ type: 'paragraph', text: cleanExplanation });
            if (item.impact) blocks.push({ type: 'callout', tone: 'success', title: 'Impact', text: sanitizePageText(item.impact) });
        });

        return { id: `cat_${slugify(category)}`, chapter_id: 'release_notes', title: category, blocks };
    }).filter(Boolean);
};
