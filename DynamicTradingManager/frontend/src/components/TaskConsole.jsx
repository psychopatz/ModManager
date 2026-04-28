import React, { useEffect, useRef, useState } from 'react';
import { Box, Paper, Typography, IconButton, LinearProgress, Fade } from '@mui/material';
import { Close as CloseIcon, Terminal as TerminalIcon } from '@mui/icons-material';
import { getTaskLogs, getTaskStatus } from '../services/api';

const TaskConsole = ({ taskId, onClose, onSuccess }) => {
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState('running');
  const [lastIndex, setLastIndex] = useState(0);
  const scrollRef = useRef(null);
  const pollingRef = useRef(null);

  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        const [logsRes, statusRes] = await Promise.all([
          getTaskLogs(taskId, lastIndex),
          getTaskStatus(taskId)
        ]);

        if (logsRes.data.length > 0) {
          setLogs(prev => [...prev, ...logsRes.data]);
          setLastIndex(prev => prev + logsRes.data.length);
        }

        setStatus(statusRes.data.status);

        if (statusRes.data.status === 'completed' || statusRes.data.status === 'failed') {
          clearInterval(pollingRef.current);
          if (statusRes.data.status === 'completed' && onSuccess) {
            onSuccess();
          }
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 1000);

    return () => clearInterval(pollingRef.current);
  }, [taskId, lastIndex]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (!taskId) return null;

  return (
    <Fade in={!!taskId}>
      <Paper
        elevation={12}
        sx={{
          position: 'fixed',
          bottom: 20,
          right: 20,
          width: { xs: '90vw', sm: 500 },
          height: 400,
          bgcolor: '#1e1e1e',
          color: '#d4d4d4',
          display: 'flex',
          flexDirection: 'column',
          zIndex: 1300,
          borderRadius: 2,
          overflow: 'hidden',
          border: '1px solid #333'
        }}
      >
        <Box sx={{ 
          p: 1.5, 
          bgcolor: '#252526', 
          display: 'flex', 
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid #333'
        }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <TerminalIcon fontSize="small" sx={{ color: '#007acc' }} />
            <Typography variant="subtitle2" sx={{ fontWeight: 600, color: '#fff' }}>
              Execution Log - {status.toUpperCase()}
            </Typography>
          </Box>
          <IconButton size="small" onClick={onClose} sx={{ color: '#aaa', '&:hover': { color: '#fff' } }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Box>

        <Box sx={{ flexGrow: 1, position: 'relative', overflow: 'hidden' }}>
          {status === 'running' && (
            <LinearProgress 
              sx={{ 
                position: 'absolute', 
                top: 0, 
                left: 0, 
                right: 0,
                height: 2,
                bgcolor: 'transparent',
                zIndex: 2,
                '& .MuiLinearProgress-bar': { bgcolor: '#007acc' }
              }} 
            />
          )}
          
          <Box
            ref={scrollRef}
            sx={{
              height: '100%',
              overflowY: 'auto',
              p: 2,
              fontFamily: '"Fira Code", "Consolas", monospace',
              fontSize: '0.85rem',
              lineHeight: 1.5,
              display: 'flex',
              flexDirection: 'column',
              '&::-webkit-scrollbar': { width: 8 },
              '&::-webkit-scrollbar-thumb': { bgcolor: '#333', borderRadius: 4 },
            }}
          >
            {logs.map((log, i) => (
              <Box key={i} sx={{ display: 'flex', gap: 1.5, mb: 0.5, flexShrink: 0 }}>
                <Typography component="span" sx={{ color: '#666', minWidth: 70, fontSize: '0.75rem' }}>
                  {new Date(log.time).toLocaleTimeString([], { hour12: false })}
                </Typography>
                <Typography component="span" sx={{ 
                  color: log.msg.includes('❌') ? '#f44336' : (log.msg.includes('✅') ? '#4caf50' : '#d4d4d4'),
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {log.msg}
                </Typography>
              </Box>
            ))}
            {logs.length === 0 && (
              <Typography sx={{ color: '#666', fontStyle: 'italic' }}>
                Waiting for output...
              </Typography>
            )}
          </Box>
        </Box>
      </Paper>
    </Fade>
  );
};

export default TaskConsole;
