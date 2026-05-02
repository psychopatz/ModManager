import { CATEGORY_HUES } from './constants';

export const buildTagTree = (catalog) => {
  const nodes = new Map();

  const ensureNode = (tag) => {
    if (!nodes.has(tag)) {
      const parts = tag.split('.');
      nodes.set(tag, {
        tag,
        label: parts[parts.length - 1],
        item_count: 0,
        current_addition: 0,
        domains: [],
        samples: [],
        children: [],
      });
    }
    return nodes.get(tag);
  };

  const sortedCatalog = [...catalog].sort((left, right) => {
    const depthDiff = left.tag.split('.').length - right.tag.split('.').length;
    if (depthDiff !== 0) {
      return depthDiff;
    }
    return left.tag.localeCompare(right.tag);
  });

  sortedCatalog.forEach((row) => {
    const parts = row.tag.split('.');
    for (let index = 0; index < parts.length; index += 1) {
      const path = parts.slice(0, index + 1).join('.');
      const node = ensureNode(path);

      if (index === parts.length - 1) {
        node.item_count = row.item_count || 0;
        node.current_addition = Number(row.current_addition || 0);
        node.domains = row.domains || [];
        node.samples = row.samples || [];
      }

      if (index > 0) {
        const parentPath = parts.slice(0, index).join('.');
        const parent = ensureNode(parentPath);
        if (!parent.children.some((child) => child.tag === path)) {
          parent.children.push(node);
        }
      }
    }
  });

  const sortChildren = (node) => {
    node.children.sort((left, right) => left.label.localeCompare(right.label));
    node.children.forEach(sortChildren);
  };

  const roots = Array.from(nodes.values()).filter((node) => !node.tag.includes('.'));
  roots.sort((left, right) => left.label.localeCompare(right.label));
  roots.forEach(sortChildren);
  return roots;
};

export const filterTree = (nodes, query) => {
  if (!query) {
    return nodes;
  }

  const lowered = query.toLowerCase();
  return nodes.reduce((acc, node) => {
    const filteredChildren = filterTree(node.children || [], query);
    const matchesSelf = (
      node.tag.toLowerCase().includes(lowered)
      || (node.domains || []).some((domain) => domain.tag.toLowerCase().includes(lowered))
      || (node.samples || []).some((sample) => (
        sample.item_id.toLowerCase().includes(lowered) || sample.name.toLowerCase().includes(lowered)
      ))
    );

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

export const lineageForTag = (tag) => {
  if (!tag) {
    return [];
  }
  const parts = tag.split('.');
  return parts.map((_, index) => parts.slice(0, index + 1).join('.'));
};

export const getTagTone = (tag) => {
  const parts = (tag || 'Misc').split('.');
  const root = parts[0] || 'Misc';
  const depth = Math.max(0, parts.length - 1);
  const hue = CATEGORY_HUES[root] ?? CATEGORY_HUES.Misc;
  const lightness = Math.max(20, 38 - (depth * 6));

  return {
    bg: `hsla(${hue}, 74%, ${lightness}%, 0.18)`,
    bgStrong: `hsla(${hue}, 78%, ${Math.max(24, lightness + 6)}%, 0.3)`,
    border: `hsla(${hue}, 78%, ${Math.min(82, lightness + 24)}%, 0.45)`,
    text: `hsl(${hue}, 90%, ${Math.min(92, lightness + 48)}%)`,
    muted: `hsla(${hue}, 82%, ${Math.min(88, lightness + 28)}%, 0.76)`,
  };
};

export const makeOverrideDraft = (row, existingOverride) => ({
  itemId: row.item_id,
  basePrice: existingOverride?.basePrice ?? '',
  stockMin: existingOverride?.stockRange?.min ?? '',
  stockMax: existingOverride?.stockRange?.max ?? '',
  tags: Array.isArray(existingOverride?.tags) ? existingOverride.tags : [],
  currentPrice: row.preview_price,
  currentStockMin: row.preview_stock_min ?? row.stock_min,
  currentStockMax: row.preview_stock_max ?? row.stock_max,
  currentTags: row.tags || [],
});

export const flattenVisibleNodes = (nodes, expandedTags, forceExpand = false, depth = 0) => nodes.flatMap((node) => {
  const row = { node, depth };
  const expanded = forceExpand || Boolean(expandedTags[node.tag] ?? depth === 0);

  if (!node.children?.length || !expanded) {
    return [row];
  }

  return [row, ...flattenVisibleNodes(node.children, expandedTags, forceExpand, depth + 1)];
});
