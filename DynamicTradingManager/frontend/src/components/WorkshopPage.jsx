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
import GitAiAssistant from './Common/GitAiAssistant';

const workshopDefaultPrompt = `Task:
1. Produce a PROFESSIONAL Steam Workshop change note.
2. Format it with [b] and [list][*] tags for Steam BBCode.

Only return the change note content.`;

const DESCRIPTION_MAX_LENGTH = 8000;
const TITLE_MAX_LENGTH = 128;

const WorkshopPage = () => {
  const workshopTargetStorageKey = 'dt_workshop_target';
  // Credentials
  const [username, setUsername] = useState(() => localStorage.getItem('dt_steam_username') || '');
  const [password, setPassword] = useState('');
  const [steamGuardCode, setSteamGuardCode] = useState('');
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


  // Section Visibility
  const [sections, setSections] = useState({
    metadata: true,
    deploy: true
  });

  const toggleSection = (name) => setSections(prev => ({ ...prev, [name]: !prev[name] }));

  // Toggles for update
  const [updateFiles, setUpdateFiles] = useState(true);
  const [updateMetadata, setUpdateMetadata] = useState(false);
  const [updatePreview, setUpdatePreview] = useState(false);
  const [modVersions, setModVersions] = useState([]);


  // UI State
  const [loading, setLoading] = useState(true);
  const [activeTaskId, setActiveTaskId] = useState(null);
  const [snackbar, setSnackbar] = useState({ open: false, message: '', severity: 'info' });
  const [latestCommitHash, setLatestCommitHash] = useState('');

  // Base API URL detection (assumes backend is on port 8000)
  const apiBaseUrl = window.location.origin.replace(':5173', ':8000');
  const buildPreviewUrl = (target) => `${apiBaseUrl}/api/workshop/preview?target=${encodeURIComponent(target)}&t=${Date.now()}`;
  const [previewUrl, setPreviewUrl] = useState('');
  const fileInputRef = useRef(null);

  const descLength = metadata.description?.length || 0;
  const isDescAtLimit = descLength >= DESCRIPTION_MAX_LENGTH;
  const titleLength = metadata.title?.length || 0;
  const isTitleAtLimit = titleLength >= TITLE_MAX_LENGTH;

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
      fetchMetadata(selectedTarget);
      fetchVersions(selectedTarget);
    }
  }, [selectedTarget]);

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


  const fetchVersions = async (target) => {
    try {
      const res = await api.getWorkshopVersions(target);
      setModVersions(res.data?.versions || []);
    } catch (err) {
      setModVersions([]);
      setSnackbar({ open: true, message: 'Failed to load module versions', severity: 'error' });
    }
  };

  const incrementVersion = async (modId, bump) => {
    try {
      const res = await api.incrementWorkshopVersion({ target: selectedTarget, mod_id: modId, bump });
      setModVersions(res.data?.versions || []);
      const updated = res.data?.updated;
      setSnackbar({
        open: true,
        message: `${updated?.name || modId}: ${updated?.old_version || '(none)'} -> ${updated?.new_version || ''}`,
        severity: 'success',
      });
    } catch (err) {
      setSnackbar({ open: true, message: err.response?.data?.detail || 'Version increment failed', severity: 'error' });
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
        steam_guard_code: steamGuardCode.trim() || undefined,
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
        <GitAiAssistant
          title="Workshop Git + AI Assistant"
          helperText="Select project, branch, and commit set to generate a workshop changelog."
          outputValue={changenote}
          onOutputChange={setChangenote}
          storageKey="workshop_git_prompt"
          defaultPrompt={workshopDefaultPrompt}
          selectedTarget={selectedTarget}
          onTargetChange={setSelectedTarget}
          availableTargets={targets}
          showSuiteToggle={(selectedTargetInfo?.sub_mods?.length > 1)}
          onLatestHash={setLatestCommitHash}
        />

        <Paper elevation={4} sx={{ borderRadius: 4, p: 3, border: '1px solid', borderColor: 'divider' }}>
          <Typography variant="h6" sx={{ fontWeight: 900, mb: 1 }}>
            Module Version Incrementer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Bump versions per module independently so workshop uploads clearly reflect updated builds.
          </Typography>

          <Stack spacing={1.5}>
            {modVersions.map((row) => (
              <Paper key={row.path} variant="outlined" sx={{ p: 1.5 }}>
                <Stack direction={{ xs: 'column', md: 'row' }} spacing={1.5} alignItems={{ md: 'center' }} justifyContent="space-between">
                  <Box>
                    <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>{row.name}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.mod_id} • Current: {row.version || 'not set'}
                    </Typography>
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" variant="outlined" onClick={() => incrementVersion(row.mod_id, 'patch')}>Patch +1</Button>
                    <Button size="small" variant="outlined" onClick={() => incrementVersion(row.mod_id, 'minor')}>Minor +1</Button>
                    <Button size="small" variant="outlined" color="warning" onClick={() => incrementVersion(row.mod_id, 'major')}>Major +1</Button>
                  </Stack>
                </Stack>
              </Paper>
            ))}
            {modVersions.length === 0 && <Alert severity="info">No module versions were discovered for this project.</Alert>}
          </Stack>
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
                  <Grid size={{ xs: 12, md: 6 }}>
                    <TextField
                      label="Mod Title"
                      fullWidth
                      value={metadata.title}
                      onChange={(e) => setMetadata({ ...metadata, title: e.target.value })}
                      disabled={!updateMetadata}
                      variant="filled"
                      inputProps={{ maxLength: TITLE_MAX_LENGTH }}
                      helperText={isTitleAtLimit
                        ? `${titleLength}/${TITLE_MAX_LENGTH} (max reached)`
                        : `${titleLength}/${TITLE_MAX_LENGTH}`}
                      error={isTitleAtLimit}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}><TextField label="Workshop ID" fullWidth value={metadata.id} onChange={(e) => setMetadata({ ...metadata, id: e.target.value })} variant="filled" /></Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <FormControl fullWidth variant="filled" disabled={!updateMetadata}>
                      <InputLabel>Visibility</InputLabel>
                      <Select value={metadata.visibility} onChange={(e) => setMetadata({ ...metadata, visibility: e.target.value })}>
                        <MenuItem value={0}>Public</MenuItem>
                        <MenuItem value={1}>Friends Only</MenuItem>
                        <MenuItem value={2}>Private</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
                <TextField
                  label="Description (Steam BBCode)"
                  fullWidth
                  multiline
                  rows={20}
                  value={metadata.description}
                  onChange={(e) => setMetadata({ ...metadata, description: e.target.value })}
                  disabled={!updateMetadata}
                  sx={{ '& .MuiInputBase-input': { fontFamily: 'monospace' } }}
                  inputProps={{ maxLength: DESCRIPTION_MAX_LENGTH }}
                  helperText={isDescAtLimit
                    ? `${descLength}/${DESCRIPTION_MAX_LENGTH} (max reached)`
                    : `${descLength}/${DESCRIPTION_MAX_LENGTH}`}
                  error={isDescAtLimit}
                />
                <TextField label="Tags (Semicolon separated)" fullWidth value={metadata.tags} onChange={(e) => setMetadata({ ...metadata, tags: e.target.value })} disabled={!updateMetadata} />
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
              <Grid size={{ xs: 12, md: 6 }}>
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
              <Grid size={{ xs: 12, md: 6 }}>
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
                      InputProps={{ endAdornment: <IconButton onClick={() => setShowPassword(!showPassword)}>{showPassword ? <VisibilityOff /> : <VisibilityIcon />}</IconButton> }}
                    />
                    <TextField
                      label="Steam Guard Code"
                      fullWidth
                      name="one-time-code"
                      id="steam-guard-code"
                      autoComplete="one-time-code"
                      value={steamGuardCode}
                      onChange={(e) => setSteamGuardCode(e.target.value)}
                      helperText="Optional. Fill this in only when SteamCMD asks for an email or authenticator code."
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
      {activeTaskId && (
        <TaskConsole 
          taskId={activeTaskId} 
          onClose={() => setActiveTaskId(null)} 
          onSuccess={() => {
            if (latestCommitHash) {
              localStorage.setItem('workshop_git_prompt_last_hash', latestCommitHash);
            }
          }}
        />
      )}
      <Snackbar open={snackbar.open} autoHideDuration={4000} onClose={() => setSnackbar({ ...snackbar, open: false })}>
        <Alert severity={snackbar.severity}>{snackbar.message}</Alert>
      </Snackbar>
    </Box>
  );
};

export default WorkshopPage;
