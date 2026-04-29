import React from 'react';
import { Typography, Box, Stack } from '@mui/material';

/**
 * A lightweight Markdown-to-MUI renderer for LLM output.
 * Supports: # H1, ## H2, ### H3, - Bullets, **Bold**, > [!tone] Callouts.
 */
const MarkdownRenderer = ({ content }) => {
    if (!content) return null;

    const lines = content.split('\n');
    const elements = [];

    let currentList = [];

    const flushList = (key) => {
        if (currentList.length > 0) {
            elements.push(
                <Stack key={`list-${key}`} spacing={0.5} sx={{ my: 1, pl: 1 }}>
                    {currentList.map((item, i) => (
                        <Typography key={i} variant="caption" sx={{ display: 'flex', gap: 1, color: 'inherit', fontFamily: 'inherit' }}>
                            <span style={{ color: '#60a5fa' }}>•</span> {processBold(item)}
                        </Typography>
                    ))}
                </Stack>
            );
            currentList = [];
        }
    };

    const processBold = (text) => {
        const parts = text.split(/(\*\*.*?\*\*)/);
        return parts.map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={i} style={{ color: '#fff', fontWeight: 800 }}>{part.slice(2, -2)}</strong>;
            }
            return part;
        });
    };

    lines.forEach((line, index) => {
        const trimmed = line.trim();
        
        // Headers
        if (trimmed.startsWith('#')) {
            flushList(index);
            const level = trimmed.match(/^#+/)[0].length;
            const text = trimmed.replace(/^#+\s*/, '');
            elements.push(
                <Typography 
                    key={index} 
                    variant={level === 1 ? 'subtitle1' : 'subtitle2'} 
                    sx={{ 
                        fontWeight: 900, 
                        mt: 1.5, mb: 0.5, 
                        color: level === 1 ? '#fff' : '#60a5fa',
                        letterSpacing: '0.02em',
                        borderBottom: level === 1 ? '1px solid rgba(255,255,255,0.1)' : 'none',
                        pb: level === 1 ? 0.5 : 0
                    }}
                >
                    {text}
                </Typography>
            );
            return;
        }

        // Bullets
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            currentList.push(trimmed.slice(2));
            return;
        }

        // Callouts: > [!tone] Title | Body
        if (trimmed.startsWith('> [!')) {
            flushList(index);
            const match = trimmed.match(/> \[!(.*?)\] (.*?) \| (.*)/);
            if (match) {
                const [_, tone, title, body] = match;
                const colors = {
                    info: '#3b82f6',
                    success: '#10b981',
                    warning: '#f59e0b',
                    danger: '#ef4444'
                };
                elements.push(
                    <Box key={index} sx={{ 
                        my: 1.5, p: 1.2, 
                        borderRadius: 1, 
                        bgcolor: 'rgba(255,255,255,0.03)', 
                        borderLeft: `3px solid ${colors[tone] || '#666'}` 
                    }}>
                        <Typography variant="caption" sx={{ fontWeight: 900, color: colors[tone] || '#fff', display: 'block', mb: 0.2, fontSize: '0.65rem' }}>
                            {title.toUpperCase()}
                        </Typography>
                        <Typography variant="caption" sx={{ opacity: 0.8, display: 'block', fontSize: '0.7rem' }}>
                            {body}
                        </Typography>
                    </Box>
                );
                return;
            }
        }

        // Regular paragraphs
        if (trimmed) {
            flushList(index);
            elements.push(
                <Typography key={index} variant="caption" sx={{ display: 'block', mb: 1, opacity: 0.9, lineHeight: 1.5 }}>
                    {processBold(line)}
                </Typography>
            );
        } else if (currentList.length > 0) {
            flushList(index);
        }
    });

    flushList('final');

    return elements;
};

export default MarkdownRenderer;
