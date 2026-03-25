import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Paper, 
  Typography, 
  Box, 
  Checkbox, 
  FormControlLabel, 
  IconButton, 
  CircularProgress,
  useTheme
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ClearIcon from '@mui/icons-material/Clear';
import DeleteIcon from '@mui/icons-material/Delete';
import RefreshIcon from '@mui/icons-material/Refresh';
import PauseIcon from '@mui/icons-material/Pause';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import { List } from 'react-window';
import { getDebugLogs } from '../services/api';

const ConsolePage = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [onlyDT, setOnlyDT] = useState(false);
  const [selectedLevels, setSelectedLevels] = useState(['Error', 'Warning', 'Lua', 'General']);
  const [selectedSystems, setSelectedSystems] = useState([]); // Empty means all if onlyDT is false, but we'll manage it
  const [autoScroll, setAutoScroll] = useState(true);
  const [isPaused, setIsPaused] = useState(false);
  const [selectedIndices, setSelectedIndices] = useState(new Set());
  const [isDragging, setIsDragging] = useState(false);
  const [dragAction, setDragAction] = useState(null); // 'select' or 'deselect'
  
  const levels_options = ['Error', 'Warning', 'Lua', 'General'];
  const systems_options = ['NPC', 'Trade', 'Economy', 'Events', 'Network', 'Core', 'UI'];
  
  const listRef = useRef(null);
  const nextOffsetRef = useRef(null);
  const containerRef = useRef(null);

  const fetchLogs = async (isInitial = false) => {
    try {
      const params = {
        limit: isInitial ? 1000 : 500,
        only_dt: onlyDT,
        offset: isInitial ? null : nextOffsetRef.current,
        levels: selectedLevels.join(','),
        systems: selectedSystems.join(',')
      };

      const response = await getDebugLogs(params);
      const { logs: newLogs, next_offset } = response.data;

      if (next_offset !== undefined) {
        nextOffsetRef.current = next_offset;
      }
      
      if (newLogs && newLogs.length > 0) {
        if (isInitial) {
          setLogs(newLogs);
        } else if (!isPaused) {
          setLogs(prev => [...prev, ...newLogs]);
        }
      }
    } catch (error) {
      console.error("Error fetching logs:", error);
    } finally {
      if (isInitial) setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(true);
    const interval = setInterval(() => {
      if (!isPaused) fetchLogs();
    }, 2000);

    return () => clearInterval(interval);
  }, [onlyDT, isPaused, selectedLevels, selectedSystems]);

  // Handle auto-scroll
  useEffect(() => {
    if (listRef.current && autoScroll && !isPaused && logs.length > 0) {
      if (typeof listRef.current.scrollToRow === 'function') {
        listRef.current.scrollToRow({ index: logs.length - 1, align: 'end' });
      }
    }
  }, [logs.length, autoScroll, isPaused]);

  const clearLogs = () => {
    setLogs([]);
    setSelectedIndices(new Set());
  };

  const clearSelection = () => {
    setSelectedIndices(new Set());
  };

  useEffect(() => {
    const handleMouseUp = () => {
      setIsDragging(false);
      setDragAction(null);
    };
    window.addEventListener('mouseup', handleMouseUp);
    return () => window.removeEventListener('mouseup', handleMouseUp);
  }, []);

  const handleSelectionStart = (index, currentSelected) => {
    setIsDragging(true);
    const newAction = currentSelected ? 'deselect' : 'select';
    setDragAction(newAction);
    
    setSelectedIndices(prev => {
      const next = new Set(prev);
      if (newAction === 'select') next.add(index);
      else next.delete(index);
      return next;
    });
  };

  const handleSelectionEnter = (index) => {
    if (!isDragging || !dragAction) return;

    setSelectedIndices(prev => {
      if (dragAction === 'select' && prev.has(index)) return prev;
      if (dragAction === 'deselect' && !prev.has(index)) return prev;

      const next = new Set(prev);
      if (dragAction === 'select') next.add(index);
      else next.delete(index);
      return next;
    });
  };


  const copySelected = () => {
    const selectedLogs = Array.from(selectedIndices)
      .sort((a, b) => a - b)
      .map(index => {
        const log = logs[index];
        const time = log.timestamp ? new Date(parseInt(log.timestamp)).toLocaleTimeString() : '???';
        return `[${time}] ${log.type.toUpperCase()}: ${log.message}`;
      })
      .join('\n');
    
    if (selectedLogs) {
      navigator.clipboard.writeText(selectedLogs);
      // Optional: Show toast
    }
  };

  const getLogColor = (type) => {
    if (!type) return '#e0e0e0';
    switch (type.toLowerCase()) {
      case 'error': return '#ff5252';
      case 'warning': 
      case 'warn': return '#ffb142';
      case 'lua': 
      case 'log': return '#4ade80';
      default: return '#e0e0e0';
    }
  };

  // rowComponent receives rowProps from List
  const LogRow = ({ index, style, selectedIndices, handleSelectionStart, handleSelectionEnter }) => {
    const log = logs[index];
    if (!log) return null;
    const isSelected = selectedIndices.has(index);

    return (
      <div 
        style={{ ...style, display: 'flex', alignItems: 'center' }}
        onMouseEnter={() => handleSelectionEnter(index)}
      >
        <Checkbox 
          size="small"
          checked={isSelected}
          onMouseDown={(e) => {
            e.preventDefault(); // Prevent text selection while dragging checkboxes
            handleSelectionStart(index, isSelected);
          }}
          sx={{ 
            p: 0, 
            mr: 1, 
            color: '#444', 
            '&.Mui-checked': { color: '#bbb' },
            transform: 'scale(0.8)',
            cursor: 'pointer'
          }}
        />
        <Box sx={{ 
          display: 'flex', 
          width: '100%', 
          borderLeft: `3px solid ${getLogColor(log.type)}`, 
          pl: 1,
          fontFamily: 'Consolas, Monaco, "Andale Mono", "Ubuntu Mono", monospace',
          fontSize: '0.85rem',
          lineHeight: '1.2rem',
          overflow: 'hidden',
          whiteSpace: 'nowrap',
          bgcolor: isSelected ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
          userSelect: 'text',
          pointerEvents: 'auto'
        }}>
          <Typography 
            component="span" 
            sx={{ 
              color: '#888', 
              fontSize: '0.75rem', 
              mr: 1,
              fontFamily: 'inherit',
              flexShrink: 0,
              minWidth: '85px'
            }}
          >
            [{log.timestamp ? new Date(parseInt(log.timestamp)).toLocaleTimeString() : '???'}]
          </Typography>
          <Typography 
            component="span" 
            sx={{ 
              color: getLogColor(log.type), 
              fontWeight: 'bold',
              mr: 1,
              fontSize: '0.75rem',
              fontFamily: 'inherit',
              flexShrink: 0
            }}
          >
            {(log.type || 'General').toUpperCase()}:
          </Typography>
          {log.dt_meta && (
            <Typography 
              component="span" 
              sx={{ 
                color: '#60a5fa', 
                fontSize: '0.75rem', 
                mr: 1,
                fontFamily: 'inherit',
                flexShrink: 0,
                bgcolor: 'rgba(96, 165, 250, 0.1)',
                px: 0.5,
                borderRadius: '2px',
                border: '1px solid rgba(96, 165, 250, 0.2)'
              }}
            >
              {log.dt_meta.system}/{log.dt_meta.specific}
            </Typography>
          )}
          <Typography 
            component="span" 
            sx={{ 
              color: '#d4d4d4',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              fontFamily: 'inherit',
              whiteSpace: 'pre-wrap'
            }}
          >
            {log.message}
          </Typography>
        </Box>
      </div>
    );
  };

  return (
    <Box sx={{ height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ mb: 2, display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
        <Typography variant="h4">System Console ({logs.length})</Typography>
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, bgcolor: '#2d2d2d', p: 1, borderRadius: 2 }}>
          <FormControlLabel
            sx={{ m: 0, mr: 1 }}
            control={
              <Checkbox 
                size="small"
                checked={onlyDT} 
                onChange={(e) => {
                  setOnlyDT(e.target.checked);
                  nextOffsetRef.current = null;
                  setLogs([]);
                  setLoading(true);
                }} 
              />
            }
            label={<Typography fontSize="0.8rem">DT Only</Typography>}
          />
          <Box sx={{ height: '24px', width: '1px', bgcolor: '#444', mx: 1 }} />
          
          <Box sx={{ display: 'flex', gap: 0.5 }}>
            {levels_options.map(level => (
              <IconButton
                key={level}
                size="small"
                onClick={() => {
                  setSelectedLevels(prev => 
                    prev.includes(level) ? prev.filter(l => l !== level) : [...prev, level]
                  );
                  nextOffsetRef.current = null;
                  setLogs([]);
                  setLoading(true);
                }}
                sx={{ 
                  fontSize: '0.7rem', 
                  borderRadius: 1,
                  px: 1,
                  color: selectedLevels.includes(level) ? getLogColor(level) : '#666',
                  bgcolor: selectedLevels.includes(level) ? 'rgba(255,255,255,0.05)' : 'transparent',
                  border: `1px solid ${selectedLevels.includes(level) ? getLogColor(level) : '#444'}`,
                  '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' }
                }}
              >
                {level.toUpperCase()}
              </IconButton>
            ))}
          </Box>
          
          {onlyDT && (
            <>
              <Box sx={{ height: '24px', width: '1px', bgcolor: '#444', mx: 1 }} />
              <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', maxWidth: '300px' }}>
                {systems_options.map(system => (
                  <IconButton
                    key={system}
                    size="small"
                    onClick={() => {
                      setSelectedSystems(prev => 
                        prev.includes(system) ? prev.filter(s => s !== system) : [...prev, system]
                      );
                      nextOffsetRef.current = null;
                      setLogs([]);
                      setLoading(true);
                    }}
                    sx={{ 
                      fontSize: '0.65rem', 
                      borderRadius: 1,
                      px: 0.8,
                      color: selectedSystems.includes(system) ? '#60a5fa' : '#666',
                      bgcolor: selectedSystems.includes(system) ? 'rgba(96, 165, 250, 0.1)' : 'transparent',
                      border: `1px solid ${selectedSystems.includes(system) ? '#60a5fa' : '#444'}`,
                      '&:hover': { bgcolor: 'rgba(96, 165, 250, 0.2)' }
                    }}
                  >
                    {system}
                  </IconButton>
                ))}
              </Box>
            </>
          )}
        </Box>

        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FormControlLabel
            control={
              <Checkbox 
                size="small"
                checked={autoScroll} 
                onChange={(e) => setAutoScroll(e.target.checked)} 
              />
            }
            label={<Typography fontSize="0.8rem">Auto-scroll</Typography>}
          />
          <IconButton 
            onClick={copySelected} 
            color="primary" 
            disabled={selectedIndices.size === 0}
            title={`Copy ${selectedIndices.size} selected lines`}
          >
            <ContentCopyIcon fontSize="small" />
          </IconButton>
          <IconButton 
            onClick={clearSelection} 
            color="error" 
            disabled={selectedIndices.size === 0}
            title="Clear Selection"
          >
            <ClearIcon sx={{ fontSize: '1rem' }} />
          </IconButton>
          <IconButton onClick={() => setIsPaused(!isPaused)} color={isPaused ? "warning" : "primary"} size="small">
            {isPaused ? <PlayArrowIcon fontSize="small" /> : <PauseIcon fontSize="small" />}
          </IconButton>
          <IconButton onClick={() => fetchLogs(true)} color="primary" size="small">
            <RefreshIcon fontSize="small" />
          </IconButton>
          <IconButton onClick={clearLogs} color="error" size="small">
            <DeleteIcon fontSize="small" />
          </IconButton>
        </Box>
      </Box>

      <Paper 
        elevation={3} 
        sx={{ 
          flexGrow: 1, 
          bgcolor: '#1e1e1e', 
          p: 1, 
          position: 'relative',
          overflow: 'hidden',
          minHeight: '200px'
        }}
        ref={containerRef}
      >
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <CircularProgress />
          </Box>
        ) : logs.length === 0 ? (
          <Typography sx={{ color: '#888', fontStyle: 'italic', p: 2 }}>No logs found...</Typography>
        ) : (
          <Box sx={{ height: '100%', width: '100%', position: 'absolute', top: 0, left: 0 }}>
            <AutoSizer>
              {({ height, width }) => (
                height > 0 && width > 0 ? (
                  <List
                    style={{ height, width, overflowX: 'hidden' }}
                    rowCount={logs.length}
                    rowHeight={22}
                    rowComponent={LogRow}
                    rowProps={{ selectedIndices, handleSelectionStart, handleSelectionEnter }} 
                    listRef={listRef}
                  />
                ) : (
                  <Box sx={{ p: 2, color: '#888' }}>Initializing container...</Box>
                )
              )}
            </AutoSizer>
          </Box>
        )}
      </Paper>
    </Box>
  );
};

// Simple AutoSizer if not installed, but usually it comes with virtualization packages
// I'll check package.json again or just install it
const AutoSizer = ({ children }) => {
  const [size, setSize] = useState({ height: 0, width: 0 });
  const ref = useRef();

  useEffect(() => {
    const observer = new ResizeObserver(entries => {
      for (let entry of entries) {
        setSize({
          height: entry.contentRect.height,
          width: entry.contentRect.width
        });
      }
    });

    if (ref.current) {
      observer.observe(ref.current);
      // Trigger initial size
      const rect = ref.current.getBoundingClientRect();
      setSize({ height: rect.height, width: rect.width });
    }
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={ref} style={{ height: '100%', width: '100%' }}>
      {children(size)}
    </div>
  );
};

export default ConsolePage;
