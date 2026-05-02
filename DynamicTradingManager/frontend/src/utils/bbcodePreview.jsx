import React from 'react';
import { Box, Divider, List, ListItem, ListItemText, Typography } from '@mui/material';

const INLINE_TAG_RE = /\[(b|i|u)\]([\s\S]*?)\[\/\1\]/i;

function parseInline(text, keyPrefix = 'inline') {
  const value = String(text || '');
  const match = value.match(INLINE_TAG_RE);
  if (!match) return [value];

  const start = match.index || 0;
  const full = match[0];
  const tag = String(match[1] || '').toLowerCase();
  const inner = match[2] || '';

  const before = value.slice(0, start);
  const after = value.slice(start + full.length);
  const children = parseInline(inner, `${keyPrefix}-inner`);

  const wrapped = (() => {
    if (tag === 'b') return <strong key={`${keyPrefix}-b`}>{children}</strong>;
    if (tag === 'i') return <em key={`${keyPrefix}-i`}>{children}</em>;
    if (tag === 'u') return <u key={`${keyPrefix}-u`}>{children}</u>;
    return <span key={`${keyPrefix}-x`}>{children}</span>;
  })();

  return [
    ...parseInline(before, `${keyPrefix}-before`),
    wrapped,
    ...parseInline(after, `${keyPrefix}-after`),
  ];
}

function parseList(lines, startIndex) {
  const items = [];
  let i = startIndex + 1;

  while (i < lines.length) {
    const line = String(lines[i] || '').trim();
    if (line.toLowerCase() === '[/list]') {
      return { next: i + 1, items };
    }

    if (line.startsWith('[*]')) {
      items.push(line.slice(3).trim());
    } else if (line) {
      if (items.length === 0) {
        items.push(line);
      } else {
        items[items.length - 1] = `${items[items.length - 1]} ${line}`.trim();
      }
    }

    i += 1;
  }

  return { next: i, items };
}

export function renderBBCodeToReact(bbcode) {
  const text = String(bbcode || '').replace(/\r\n/g, '\n');
  const lines = text.split('\n');
  const nodes = [];

  let i = 0;
  while (i < lines.length) {
    const rawLine = lines[i] || '';
    const line = rawLine.trim();

    if (!line) {
      i += 1;
      continue;
    }

    if (/^\[hr\]\[\/hr\]$/i.test(line)) {
      nodes.push(<Divider key={`hr-${i}`} sx={{ my: 1.25 }} />);
      i += 1;
      continue;
    }

    if (/^\[h1\][\s\S]*\[\/h1\]$/i.test(line)) {
      const textValue = line.replace(/^\[h1\]/i, '').replace(/\[\/h1\]$/i, '');
      nodes.push(
        <Typography key={`h1-${i}`} variant="h5" sx={{ fontWeight: 900, mt: 0.5, mb: 1 }}>
          {parseInline(textValue, `h1-${i}`)}
        </Typography>
      );
      i += 1;
      continue;
    }

    if (/^\[h2\][\s\S]*\[\/h2\]$/i.test(line)) {
      const textValue = line.replace(/^\[h2\]/i, '').replace(/\[\/h2\]$/i, '');
      nodes.push(
        <Typography key={`h2-${i}`} variant="subtitle1" sx={{ fontWeight: 800, mt: 1.25, mb: 0.75 }}>
          {parseInline(textValue, `h2-${i}`)}
        </Typography>
      );
      i += 1;
      continue;
    }

    if (/^\[list\]$/i.test(line)) {
      const parsed = parseList(lines, i);
      nodes.push(
        <List key={`list-${i}`} dense sx={{ py: 0, pl: 2.5, listStyleType: 'disc' }}>
          {parsed.items.map((item, index) => (
            <ListItem key={`list-${i}-${index}`} sx={{ display: 'list-item', py: 0.2, pl: 0 }}>
              <ListItemText
                primaryTypographyProps={{ variant: 'body2', sx: { my: 0.1 } }}
                primary={parseInline(item, `li-${i}-${index}`)}
              />
            </ListItem>
          ))}
        </List>
      );
      i = parsed.next;
      continue;
    }

    nodes.push(
      <Typography key={`p-${i}`} variant="body2" sx={{ whiteSpace: 'pre-wrap', mb: 0.5 }}>
        {parseInline(line, `p-${i}`)}
      </Typography>
    );
    i += 1;
  }

  if (nodes.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No BBCode content to preview yet.
      </Typography>
    );
  }

  return <Box>{nodes}</Box>;
}