import { Box, Typography, Stack, CircularProgress } from '@mui/material';
import { 
    AutoAwesome as AiStatusIcon, 
} from '@mui/icons-material';
import MarkdownRenderer from './MarkdownRenderer';

const AiMonitor = ({ title, thinking, content, status, isAnyStreaming }) => {
    if (!isAnyStreaming && !thinking && !content) return null;

    return (
        <Box sx={{ 
            border: '1px solid rgba(59, 130, 246, 0.3)', 
            borderRadius: 2, 
            overflow: 'hidden', 
            mb: 2, 
            bgcolor: 'rgba(59, 130, 246, 0.05)',
            boxShadow: isAnyStreaming ? '0 0 15px rgba(59, 130, 246, 0.1)' : 'none'
        }}>
            <Box sx={{ 
                bgcolor: 'rgba(59, 130, 246, 0.1)', 
                px: 1.5, py: 0.8, 
                borderBottom: '1px solid rgba(59, 130, 246, 0.2)', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between'
            }}>
                <Stack direction="row" spacing={1} alignItems="center">
                    <AiStatusIcon sx={{ fontSize: 14, color: isAnyStreaming ? '#60a5fa' : '#34d399' }} />
                    <Typography variant="caption" sx={{ fontWeight: 800, letterSpacing: '0.05em', color: '#60a5fa' }}>
                        AI MONITOR: {title || (isAnyStreaming ? 'PROCESSING' : 'IDLE')}
                    </Typography>
                </Stack>
                {status === 'streaming' && (
                    <Stack direction="row" spacing={1} alignItems="center">
                        <CircularProgress size={10} thickness={6} sx={{ color: '#60a5fa' }} />
                        <Typography variant="caption" sx={{ fontSize: '0.6rem', color: '#60a5fa', fontWeight: 800 }}>LIVE</Typography>
                    </Stack>
                )}
            </Box>
            
            <Stack spacing={0}>
                {thinking && (
                    <Box sx={{ p: 1.5, maxHeight: 100, overflowY: 'auto', borderBottom: content ? '1px solid rgba(59, 130, 246, 0.1)' : 'none' }}>
                        <Typography variant="caption" sx={{ opacity: 0.5, display: 'block', mb: 0.5, fontWeight: 800, fontSize: '0.6rem', color: '#60a5fa' }}>REASONING</Typography>
                        <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.7rem', color: '#94a3b8', whiteSpace: 'pre-wrap' }}>
                            {thinking}
                        </Typography>
                    </Box>
                )}
                <Box sx={{ p: 1.5, maxHeight: 400, overflowY: 'auto', bgcolor: 'rgba(0,0,0,0.2)' }}>
                    <Typography variant="caption" sx={{ opacity: 0.5, display: 'block', mb: 0.5, fontWeight: 800, fontSize: '0.6rem', color: '#60a5fa' }}>LIVE OUTPUT</Typography>
                    <Box sx={{ color: '#e2e8f0' }}>
                        {content ? (
                            <MarkdownRenderer content={content} />
                        ) : (
                            <Typography variant="caption" sx={{ fontFamily: 'monospace', fontSize: '0.75rem', opacity: 0.5 }}>
                                {isAnyStreaming ? "Initializing neural patterns..." : "Standby..."}
                            </Typography>
                        )}
                        {status === 'streaming' && <span className="streaming-cursor">|</span>}
                    </Box>
                </Box>
            </Stack>

            <style>
                {`
                @keyframes pulse {
                    0% { opacity: 1; }
                    50% { opacity: 0; }
                    100% { opacity: 1; }
                }
                .streaming-cursor {
                    display: inline-block;
                    width: 2px;
                    margin-left: 2px;
                    color: #60a5fa;
                    animation: pulse 1s infinite;
                }
                `}
            </style>
        </Box>
    );
};

export default AiMonitor;
