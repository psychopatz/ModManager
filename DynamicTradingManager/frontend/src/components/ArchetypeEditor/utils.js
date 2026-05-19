export const DRAG_MIME = 'application/x-dt-archetype-entry';

export const allocationKey = (entry) => {
  if (entry.kind === 'item') {
    return `item:${entry.item_id}`;
  }
  return `tag:${(entry.tags || []).join('|')}`;
};

export const cloneAllocations = (allocations = []) => allocations.map((entry) => ({
  kind: entry.kind,
  count: Number(entry.count || 1),
  tags: Array.isArray(entry.tags) ? [...entry.tags] : undefined,
  item_id: entry.item_id,
  item_name: entry.item_name,
  label: entry.label,
  matched_item_count: Number(entry.matched_item_count || 0),
  sample_items: Array.isArray(entry.sample_items) ? [...entry.sample_items] : [],
}));

export const cloneTags = (values = []) => values.map((value) => String(value));
export const cloneWants = (values = []) => values.map((row) => ({
  tag: row.tag || '',
  multiplier: String(row.multiplier ?? ''),
}));

export const createDraftFromArchetype = (archetype) => ({
  name: archetype?.name || '',
  allocations: cloneAllocations(archetype?.allocations || []),
  expertTags: cloneTags(archetype?.expert_tags || []),
  forbid: cloneTags(archetype?.forbid || []),
  wants: cloneWants(archetype?.wants || []),
});

export const normalizeAllocationsForSave = (allocations = []) => allocations.map((entry) => {
  if (entry.kind === 'item') {
    return {
      kind: 'item',
      item_id: entry.item_id,
      count: Math.max(1, Number(entry.count || 1)),
    };
  }

  return {
    kind: 'tag',
    tags: Array.isArray(entry.tags) ? entry.tags.filter(Boolean) : [],
    count: Math.max(1, Number(entry.count || 1)),
  };
});

export const buildSavePayload = (draft, archetypeId = '') => ({
  name: String(draft.name || '').trim() || archetypeId,
  allocations: normalizeAllocationsForSave(draft.allocations || []),
  expert_tags: (draft.expertTags || []).map((value) => String(value).trim()).filter(Boolean),
  forbid: (draft.forbid || []).map((value) => String(value).trim()).filter(Boolean),
  wants: (draft.wants || [])
    .map((row) => ({
      tag: String(row.tag || '').trim(),
      multiplier: Number(row.multiplier),
    }))
    .filter((row) => row.tag),
});

export const issueKey = (issue) => JSON.stringify({
  code: issue.code,
  field: issue.field,
  value: issue.value,
  path: issue.path,
});

export const buildTagTree = (rows) => {
  const nodeMap = new Map();

  const ensureNode = (tag) => {
    if (!nodeMap.has(tag)) {
      const parts = tag.split('.');
      nodeMap.set(tag, {
        tag,
        label: parts[parts.length - 1],
        children: [],
        meta: null,
      });
    }
    return nodeMap.get(tag);
  };

  rows.forEach((row) => {
    const parts = row.tag.split('.');
    const node = ensureNode(row.tag);
    node.meta = row;

    for (let index = 1; index < parts.length; index += 1) {
      const parentTag = parts.slice(0, index).join('.');
      const childTag = parts.slice(0, index + 1).join('.');
      const parent = ensureNode(parentTag);
      const child = ensureNode(childTag);
      if (!parent.children.some((candidate) => candidate.tag === child.tag)) {
        parent.children.push(child);
      }
    }
  });

  const sortNode = (node) => {
    node.children.sort((left, right) => left.label.localeCompare(right.label));
    node.children.forEach(sortNode);
  };

  const roots = Array.from(nodeMap.values()).filter((node) => !node.tag.includes('.'));
  roots.sort((left, right) => left.label.localeCompare(right.label));
  roots.forEach(sortNode);
  return roots;
};

export const filterTree = (nodes, query) => {
  if (!query) {
    return nodes;
  }

  const lowered = query.toLowerCase();

  return nodes.reduce((acc, node) => {
    const filteredChildren = filterTree(node.children || [], query);
    const sampleHit = (node.meta?.sample_items || []).some((sample) => (
      sample.item_id.toLowerCase().includes(lowered)
      || sample.name.toLowerCase().includes(lowered)
    ));
    const matchesSelf = node.tag.toLowerCase().includes(lowered) || sampleHit;

    if (!matchesSelf && !filteredChildren.length) {
      return acc;
    }

    acc.push({
      ...node,
      children: filteredChildren,
    });
    return acc;
  }, []);
};
