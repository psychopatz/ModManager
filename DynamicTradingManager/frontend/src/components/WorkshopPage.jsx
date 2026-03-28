import React, { useState, useEffect, useRef, useMemo } from 'react';
import { 
  Box, 
  Typography, 
  Paper, 
  Button, 
  TextField, 
  Stack, 
  Divider, 
  Alert,
  Grid,
  Snackbar,
  InputAdornment,
  IconButton,
  Switch,
  FormControlLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Tooltip,
  Chip,
  Collapse,
  Checkbox,
  FormGroup
} from '@mui/material';
import { 
  CloudUpload as UploadIcon, 
  Build as BuildIcon, 
  Person as PersonIcon, 
  Lock as LockIcon,
  Visibility as VisibilityIcon,
  VisibilityOff,
  Info as InfoIcon,
  Photo as PhotoIcon,
  Edit as EditIcon,
  Sync as SyncIcon,
  AutoAwesome as AiIcon,
  ContentCopy as CopyIcon,
  History as HistoryIcon,
  DeviceHub as BranchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  FilterList as FilterIcon,
  Clear as ClearIcon
} from '@mui/icons-material';
import * as api from '../services/api';
import TaskConsole from './TaskConsole';

const WorkshopPage = () => {
  const workshopTargetStorageKey = 'dt_workshop_target';
  // Credentials
  const [username, setUsername] = useState(() => localStorage.getItem('dt_steam_username') || '');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    localStorage.setItem('dt_steam_username', username);
  }, [username]);
  
  // Metadata
  const [metadata, setMetadata] = useState({
    title: '',
    description: '',
    tags: '',
    visibility: 0,
    id: ''
  });
  const [targets, setTargets] = useState([]);
  const [selectedTarget, setSelectedTarget] = useState(() => localStorage.getItem(workshopTargetStorageKey) || '');
  const [changenote, setChangenote] = useState('Mod update pushed via Dynamic Trading Manager');
  const [showPromptEditor, setShowPromptEditor] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState(() => {
    return localStorage.getItem('dt_workshop_system_prompt') || `
Task: 
1. Produce a PROFESSIONAL Steam Workshop change note (short, maximum 3-5 bullet points).
2. Format it with [b] and [list][*] tags for Steam BBCode.

Only return the change note content.`;
  });

  useEffect(() => {
    localStorage.setItem('dt_workshop_system_prompt', systemPrompt);
  }, [systemPrompt]);
  
  // Section Visibility
  const [sections, setSections] = useState({
    history: true,
    metadata: true,
    ai: true,
    deploy: true
  });

  const toggleSection = (name) => setSections(prev => ({ ...prev, [name]: !prev[name] }));

  // Toggles for update
  const [updateFiles, setUpdateFiles] = useState(true);
  const [updateMetadata, setUpdateMetadata] = useState(false);
  const [updatePreview, setUpdatePreview] = useState(false);
  
  // Git & AI
  const [gitChanges, setGitChanges] = useState(null);
  const [branches, setBranches] = useState([]);
  const [selectedBranch, setSelectedBranch] = useState('develop');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Selection & Dragging
  const [selectedHashes, setSelectedHashes] = useState(new Set());
  const [isDragging, setIsDragging] = useState(false);
  const [dragAction, setDragAction] = useState(null); // 'select' or 'deselect'

  // Filters
  const [filters, setFilters] = useState({
    feat: true,
    fix: true,
    refactor: false,
    chore: false,
    docs: false,
    other: false
  });

  const handleFilterChange = (type) => setFilters(prev => ({ ...prev, [type]: !prev[type] }));

  // Filtered Commits
  const filteredCommits = useMemo(() => {
    if (!gitChanges?.commits) return [];
    return gitChanges.commits.filter(c => filters[c.type]);
  }, [gitChanges, filters]);

  // Selection Handlers
  useEffect(() => {
    const handleMouseUp = () => {
      setIsDragging(false);
      setDragAction(null);
    };
    window.addEventListener('mouseup', handleMouseUp);
    return () => window.removeEventListener('mouseup', handleMouseUp);
  }, []);

  const handleSelectionStart = (hash, currentSelected) => {
    setIsDragging(true);
    const newAction = currentSelected ? 'deselect' : 'select';
    setDragAction(newAction);
    
    setSelectedHashes(prev => {
      const next = new Set(prev);
      if (newAction === 'select') next.add(hash);
      else next.delete(hash);
      return next;
    });
  };

  const handleSelectionEnter = (hash) => {
    if (!isDragging || !dragAction) return;
    setSelectedHashes(prev => {
      const next = new Set(prev);
      if (dragAction === 'select') next.add(hash);
      else next.delete(hash);
      return next;
    });
  };

  const clearSelection = () => {
    setSelectedHashes(new Set());
    setSnackbar({ open: true, message: 'Selection cleared!', severity: 'info' });
  };

  // UI State
  const [loading, setLoading] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  
  // Base API URL detection (assumes backend is on port 8000)
  const apiBaseUrl = window.location.origin.replace(':5173', ':8000');
  const buildPreviewUrl = (target) => `${apiBaseUrl}/api/workshop/preview?target=${encodeURIComponent(target)}&t=${Date.now()}`;
  const [previewUrl, setPreviewUrl] = useState('');
  const fileInputRef = useRef(null);
  const selectedTargetInfo = useMemo(
    () => targets.find((target) => target.key === selectedTarget) || null,
    [targets, selectedTarget]
  );

  useEffect(() => {
    fetchTargets();
  }, []);

  useEffect(() => {
    if (selectedTarget) {
      localStorage.setItem(workshopTargetStorageKey, selectedTarget);
      setPreviewUrl(buildPreviewUrl(selectedTarget));
      setSelectedHashes(new Set());
      fetchMetadata(selectedTarget);
      fetchBranches(selectedTarget);
    }
  }, [selectedTarget]);

  useEffect(() => {
    if (selectedTarget && selectedBranch) {
        fetchGitChanges(selectedBranch, selectedTarget);
    }
  }, [selectedBranch, selectedTarget]);

  const fetchTargets = async () => {
    setLoading(true);
    try {
      const res = await api.getWorkshopTargets();
      const availableTargets = res.data?.targets || [];
      const defaultTarget = res.data?.default_target || availableTargets[0]?.key || '';
      const storedTarget = localStorage.getItem(workshopTargetStorageKey);
      const nextTarget = availableTargets.some((target) => target.key === storedTarget) ? storedTarget : defaultTarget;
      setTargets(availableTargets);
      setSelectedTarget(nextTarget);
      if (!nextTarget) {
        setLoading(false);
      }
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to discover workshop projects', severity: 'error' });
      setLoading(false);
    }
  };

  const fetchMetadata = async (target) => {
    setLoading(true);
    setMetadata({
      title: '',
      description: '',
      tags: '',
      visibility: 0,
      id: ''
    });
    try {
      const res = await api.getWorkshopMetadata(target);
      setMetadata(prev => ({ ...prev, ...res.data }));
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to load mod metadata', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const fetchBranches = async (target) => {
    try {
      const res = await api.getGitBranches(target);
      setBranches(res.data);
      if (res.data.includes('develop')) {
        setSelectedBranch('develop');
      } else if (res.data.length > 0) {
        setSelectedBranch(res.data[0]);
      }
    } catch (err) {
      console.error('Failed to fetch branches');
    }
  };

  const fetchGitChanges = async (branch, target) => {
    try {
      const res = await api.getGitChanges(branch, target);
      setGitChanges(res.data);
    } catch (err) {
      console.error('Failed to fetch git changes');
    }
  };

  const handleSync = async () => {
    if (!selectedTarget) return;
    setLoading(true);
    try {
      const res = await api.getWorkshopSync(selectedTarget, metadata.id || undefined);
      setMetadata(prev => ({ ...prev, ...res.data }));
      if (res.data.preview_url) setPreviewUrl(res.data.preview_url);
      setUpdateMetadata(true);
      setSnackbar({ open: true, message: 'Synced from Steam', severity: 'success' });
    } catch (err) {
      setSnackbar({ open: true, message: 'Sync failed', severity: 'error' });
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateAiDescription = async () => {
    if (!window.puter) {
      setSnackbar({ open: true, message: 'Puter.js not loaded. Check internet.', severity: 'error' });
      return;
    }
    
    setIsGenerating(true);
    try {
      const prompt = `
        Context: I am updating a Project Zomboid mod called "${metadata.title}".
        Below is the git diff/status of my CURRENT uncommitted changes:
        ${gitChanges?.status}\n${gitChanges?.summary}\n${gitChanges?.detail?.substring(0, 2000)}
        
        Reference: Here are the RECENT FILTERED commits for context (Selected types: ${Object.entries(filters).filter(([k,v])=>v).map(([k])=>k).join(',')}):
        ${filteredCommits.map(c => c.raw).join('\n')}
        
        ${systemPrompt}
      `;
      
      const response = await window.puter.ai.chat(prompt);
      setChangenote(response.message.content.trim());
      setSnackbar({ open: true, message: 'AI Change Note generated!', severity: 'success' });
    } catch (err) {
      setSnackbar({ open: true, message: 'AI Generation failed', severity: 'error' });
    } finally {
      setIsGenerating(false);
    }
  };

  const copyGitSummary = () => {
    const targetCommits = selectedHashes.size > 0 
      ? filteredCommits.filter(c => selectedHashes.has(c.hash))
      : filteredCommits;
      
    const historyText = targetCommits.map(c => c.raw).join('\n');
    const summary = `Selected Project History (${selectedTargetInfo?.name || 'Project'} | Branch: ${selectedBranch}):\n${historyText}`;
    navigator.clipboard.writeText(summary);
    setSnackbar({ open: true, message: `Copied ${targetCommits.length} commits!`, severity: 'success' });
  };

  const handleImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file || !selectedTarget) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.uploadWorkshopImage(formData, selectedTarget);
      setPreviewUrl(buildPreviewUrl(selectedTarget));
      setUpdatePreview(true);
      setSnackbar({ open: true, message: 'Image uploaded', severity: 'success' });
    } catch (err) {
      setSnackbar({ open: true, message: 'Upload failed', severity: 'error' });
    }
  };

  const handlePush = async () => {
    try {
      const payload = {
        target: selectedTarget,
        workshop_id: metadata.id || undefined,
        username,
        password: password || undefined,
        changenote,
        update_files: updateFiles,
        update_metadata: updateMetadata,
        update_preview: updatePreview,
        ...(updateMetadata ? {
          title: metadata.title,
          description: metadata.description,
          tags: metadata.tags,
          visibility: metadata.visibility
        } : {})
      };
      const res = await api.triggerWorkshopPush(payload);
      if (res.data.task_id) {
        setActiveTaskId(res.data.task_id);
      }
    } catch (err) {
        setSnackbar({ open: true, message: err.response?.data?.detail || 'Push failed', severity: 'error' });
    }
  };

  const onPushSubmit = (e) => {
    e.preventDefault();
    handlePush();
  };

  if (loading) return <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}><CircularProgress /></Box>;

  return (
    <Box sx={{ width: '100%', minHeight: '100vh', py: 4, px: { xs: 2, md: 4 } }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 6 }}>
        <Box>
          <Typography variant="h3" sx={{ fontWeight: 950, letterSpacing: '-2px', color: 'primary.main' }}>
            WORKSHOP STUDIO
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" sx={{ fontWeight: 600 }}>
             Project: <span style={{ color: '#fff', background: '#333', padding: '2px 8px', borderRadius: '4px' }}>{selectedTargetInfo?.name || metadata.title || 'Unknown'}</span>
          </Typography>
        </Box>
        <Stack direction="row" spacing={2} alignItems="center">
           <FormControl size="small" sx={{ minWidth: 220 }}>
             <InputLabel>Project</InputLabel>
             <Select value={selectedTarget} label="Project" onChange={(e) => setSelectedTarget(e.target.value)}>
               {targets.map((target) => (
                 <MenuItem key={target.key} value={target.key}>
                   {target.name}
                 </MenuItem>
               ))}
             </Select>
           </FormControl>
           <Button variant="outlined" startIcon={<SyncIcon />} onClick={handleSync} sx={{ borderRadius: 3, fontWeight: 700 }}>Refresh</Button>
           <Button
             variant="contained"
             startIcon={<VisibilityIcon />}
             disabled={!metadata.id}
             onClick={() => window.open(`https://steamcommunity.com/sharedfiles/filedetails/?id=${metadata.id}`, '_blank')}
             sx={{ borderRadius: 3, fontWeight: 700, px: 3 }}
           >
             Workshop Link
           </Button>
        </Stack>
      </Box>

      <Stack spacing={4}>
        {/* 1. Project Chronicle with Filters */}
        <Paper elevation={4} sx={{ borderRadius: 4, overflow: 'hidden', border: '1px solid', borderColor: 'divider' }}>
          <Box sx={{ p: 2, px: 3, bgcolor: 'rgba(33, 150, 243, 0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleSection('history')}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, display: 'flex', alignItems: 'center', gap: 2 }}>
              <HistoryIcon color="primary" /> {selectedBranch.toUpperCase()} PROJECT CHRONICLE
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" onClick={(e) => e.stopPropagation()}>
               <FormControl size="small" sx={{ minWidth: 150 }}>
                 <Select value={selectedBranch} onChange={(e) => setSelectedBranch(e.target.value)} sx={{ borderRadius: 2, fontSize: '0.8rem', fontWeight: 700, bgcolor: 'background.paper' }} startAdornment={<BranchIcon sx={{ mr: 1, fontSize: '1rem' }} />}>
                    {branches.map(b => <MenuItem key={b} value={b}>{b}</MenuItem>)}
                  </Select>
               </FormControl>
               <Button size="small" variant="outlined" startIcon={<CopyIcon />} onClick={copyGitSummary}>{selectedHashes.size > 0 ? `Copy Selected (${selectedHashes.size})` : 'Copy Filtered'}</Button>
               {selectedHashes.size > 0 && <Button size="small" variant="text" color="error" startIcon={<ClearIcon />} onClick={clearSelection}>Clear All</Button>}
               {sections.history ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </Stack>
          </Box>
          <Collapse in={sections.history}>
            <Box sx={{ borderBottom: '1px solid', borderColor: 'divider', p: 1, px: 3, bgcolor: 'rgba(0,0,0,0.01)' }}>
               <FormGroup row>
                 <Typography variant="caption" sx={{ alignSelf: 'center', mr: 2, fontWeight: 800 }}>SHOW TYPES:</Typography>
                 {Object.keys(filters).map(f => (
                   <FormControlLabel
                     key={f}
                     control={<Checkbox size="small" checked={filters[f]} onChange={() => handleFilterChange(f)} color="primary" />}
                     label={<Typography variant="caption" fontWeight={filters[f] ? 800 : 400}>{f.toUpperCase()}</Typography>}
                     sx={{ mr: 3 }}
                   />
                 ))}
               </FormGroup>
            </Box>
            <Box sx={{ height: 400, overflow: 'auto', p: 1, bgcolor: '#010409', color: '#e6edf3' }}>
                {filteredCommits.length > 0 ? (
                  filteredCommits.map((c) => {
                    const isSelected = selectedHashes.has(c.hash);
                    return (
                      <Box 
                        key={c.hash} 
                        onMouseEnter={() => handleSelectionEnter(c.hash)}
                        sx={{ 
                          display: 'flex', 
                          alignItems: 'center', 
                          py: 0.5, 
                          px: 2,
                          bgcolor: isSelected ? 'rgba(33, 150, 243, 0.15)' : 'transparent',
                          '&:hover': { bgcolor: isSelected ? 'rgba(33, 150, 243, 0.2)' : 'rgba(255,255,255,0.03)' },
                          cursor: 'default',
                          userSelect: 'none'
                        }}
                      >
                        <Checkbox 
                          size="small" 
                          checked={isSelected}
                          onMouseDown={(e) => {
                            e.preventDefault();
                            handleSelectionStart(c.hash, isSelected);
                          }}
                          sx={{ p: 0.5, mr: 1, color: 'rgba(255,255,255,0.3)' }} 
                        />
                        <Typography 
                          component="pre" 
                          sx={{ 
                            fontSize: '0.85rem', 
                            whiteSpace: 'pre-wrap', 
                            fontFamily: "'JetBrains Mono', monospace",
                            m: 0,
                            color: isSelected ? '#fff' : '#e6edf3'
                          }}
                        >
                          {c.raw}
                        </Typography>
                      </Box>
                    );
                  })
                ) : (
                  <Box sx={{ p: 4, textAlign: 'center' }}>
                     <Typography color="text.secondary">No commits match your active filters.</Typography>
                  </Box>
                )}
            </Box>
          </Collapse>
        </Paper>

        {/* 2. AI Release Assistant */}
        <Paper elevation={4} sx={{ borderRadius: 4, bgcolor: 'background.paper', border: '1px solid', borderColor: 'primary.light', overflow: 'hidden' }}>
          <Box sx={{ p: 2, px: 3, background: 'linear-gradient(90deg, #2196F3 0%, #21CBF3 100%)', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleSection('ai')}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, display: 'flex', alignItems: 'center', gap: 2 }}>
              <AiIcon /> AI RELEASE CO-PILOT
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" onClick={(e) => e.stopPropagation()}>
              <Button variant="outlined" size="small" startIcon={<EditIcon />} onClick={() => setShowPromptEditor(!showPromptEditor)} sx={{ color: 'white', borderColor: 'white', fontWeight: 800 }}>
                {showPromptEditor ? 'Hide Prompt' : 'Edit Prompt'}
              </Button>
              <Button variant="contained" size="small" onClick={handleGenerateAiDescription} disabled={isGenerating || !gitChanges} sx={{ bgcolor: 'white', color: 'primary.main', fontWeight: 800 }}>
                {isGenerating ? <CircularProgress size={16} /> : 'Generate with Selected'}
              </Button>
              {sections.ai ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </Stack>
          </Box>
          <Collapse in={sections.ai}>
            <Box sx={{ p: 4 }}>
               <Collapse in={showPromptEditor}>
                  <Box sx={{ mb: 4, p: 2, bgcolor: 'rgba(33, 150, 243, 0.05)', borderRadius: 3, border: '1px dashed', borderColor: 'primary.main' }}>
                    <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 900, color: 'primary.main' }}>SYSTEM INSTRUCTIONS (AI GUIDELINES)</Typography>
                    <TextField fullWidth multiline rows={4} value={systemPrompt} onChange={(e) => setSystemPrompt(e.target.value)} variant="standard" placeholder="How should the AI behave? (e.g., 'Be funny', 'Be concise', 'Exclude refactors')" sx={{ '& .MuiInputBase-root': { fontSize: '0.8rem', fontFamily: 'monospace' } }} />
                  </Box>
               </Collapse>
               <Typography variant="caption" sx={{ display: 'block', mb: 1, fontWeight: 900, color: 'text.secondary' }}>GENERATED CHANGE NOTE</Typography>
               <TextField fullWidth multiline rows={8} value={changenote} onChange={(e) => setChangenote(e.target.value)} variant="outlined" sx={{ borderRadius: 2 }} placeholder="AI will use your filtered history below..." />
            </Box>
          </Collapse>
        </Paper>

        {/* 3. Mod Content */}
        <Paper elevation={4} sx={{ borderRadius: 4, overflow: 'hidden' }}>
          <Box sx={{ p: 2, px: 3, bgcolor: 'rgba(0,0,0,0.02)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }} onClick={() => toggleSection('metadata')}>
            <Typography variant="subtitle1" sx={{ fontWeight: 900, display: 'flex', alignItems: 'center', gap: 2 }}>
              <EditIcon color="primary" /> WORKSHOP WEB CONTENT
            </Typography>
            {sections.metadata ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </Box>
          <Collapse in={sections.metadata}>
            <Box sx={{ p: 4 }}>
               <Stack spacing={4}>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}><TextField label="Mod Title" fullWidth value={metadata.title} onChange={(e) => setMetadata({...metadata, title: e.target.value})} disabled={!updateMetadata} variant="filled" /></Grid>
                    <Grid item xs={12} md={3}><TextField label="Workshop ID" fullWidth value={metadata.id} onChange={(e) => setMetadata({...metadata, id: e.target.value})} variant="filled" /></Grid>
                    <Grid item xs={12} md={3}>
                      <FormControl fullWidth variant="filled" disabled={!updateMetadata}>
                        <InputLabel>Visibility</InputLabel>
                        <Select value={metadata.visibility} onChange={(e) => setMetadata({...metadata, visibility: e.target.value})}>
                          <MenuItem value={0}>Public</MenuItem>
                          <MenuItem value={1}>Friends Only</MenuItem>
                          <MenuItem value={2}>Private</MenuItem>
                        </Select>
                      </FormControl>
                    </Grid>
                  </Grid>
                  <TextField label="Description (Steam BBCode)" fullWidth multiline rows={20} value={metadata.description} onChange={(e) => setMetadata({...metadata, description: e.target.value})} disabled={!updateMetadata} sx={{ '& .MuiInputBase-input': { fontFamily: 'monospace' } }} />
                  <TextField label="Tags (Semicolon separated)" fullWidth value={metadata.tags} onChange={(e) => setMetadata({...metadata, tags: e.target.value})} disabled={!updateMetadata} />
               </Stack>
            </Box>
          </Collapse>
        </Paper>

        {/* 4. Deployment Center */}
        <Paper elevation={10} sx={{ p: 4, borderRadius: 5, border: '2px solid', borderColor: 'divider' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4, cursor: 'pointer' }} onClick={() => toggleSection('deploy')}>
             <Typography variant="h5" sx={{ fontWeight: 900, letterSpacing: '-1px' }}>READY TO DEPLOY</Typography>
             {sections.deploy ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </Box>
          <Collapse in={sections.deploy}>
             <Grid container spacing={4}>
                <Grid item xs={12} md={6}>
                  <Stack spacing={3}>
                    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                      <FormControlLabel control={<Switch checked={updateFiles} onChange={(e) => setUpdateFiles(e.target.checked)} />} label={<Typography fontWeight={800}>Update Scripts & Binaries</Typography>} />
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                      <FormControlLabel control={<Switch checked={updateMetadata} onChange={(e) => setUpdateMetadata(e.target.checked)} />} label={<Typography fontWeight={800}>Update Metadata</Typography>} />
                    </Paper>
                    <Paper variant="outlined" sx={{ p: 2, borderRadius: 3 }}>
                      <FormControlLabel control={<Switch checked={updatePreview} onChange={(e) => setUpdatePreview(e.target.checked)} />} label={<Typography fontWeight={800}>Update Poster Image</Typography>} />
                      <Collapse in={updatePreview}>
                         <Box sx={{ mt: 2, borderRadius: 3, overflow: 'hidden', border: '1px solid #eee' }}>
                           <img src={previewUrl} style={{ width: '100%', display: 'block' }} alt="Poster Preview" />
                         </Box>
                         <Button fullWidth variant="text" size="small" onClick={() => fileInputRef.current.click()} sx={{ mt: 1 }}>Change Image</Button>
                      </Collapse>
                    </Paper>
                  </Stack>
                </Grid>
                <Grid item xs={12} md={6}>
                  <form onSubmit={onPushSubmit}>
                    <Stack spacing={3}>
                      <TextField 
                        label="Steam User" 
                        fullWidth 
                        name="username"
                        id="steam-username"
                        autoComplete="username" 
                        value={username} 
                        onChange={(e) => setUsername(e.target.value)} 
                        variant="outlined" 
                      />
                      <TextField 
                        label="Steam Password" 
                        type={showPassword ? 'text' : 'password'} 
                        fullWidth 
                        name="password"
                        id="steam-password"
                        autoComplete="current-password"
                        value={password} 
                        onChange={(e) => setPassword(e.target.value)} 
                        InputProps={{ endAdornment: <IconButton onClick={()=>setShowPassword(!showPassword)}>{showPassword ? <VisibilityOff /> : <VisibilityIcon />}</IconButton> }}
                      />
                      <Button 
                        variant="contained" 
                        color="primary" 
                        fullWidth 
                        size="large" 
                        type="submit"
                        disabled={!selectedTarget || !metadata.id || !username || (!updateFiles && !updateMetadata && !updatePreview)} 
                        sx={{ py: 2.5, borderRadius: 4, fontWeight: 900 }}
                      >
                         PUSH UPDATE TO STEAM
                      </Button>
                    </Stack>
                  </form>
                </Grid>
             </Grid>
          </Collapse>
        </Paper>
      </Stack>

      <input type="file" accept="image/*.png" style={{ display: 'none' }} ref={fileInputRef} onChange={handleImageUpload} />
      {activeTaskId && <TaskConsole taskId={activeTaskId} onClose={() => setActiveTaskId(null)} />}
      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default WorkshopPage;
