import React from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from '@mui/material';

const WorkshopPublishConfirmDialog = ({
  open,
  isPushing,
  onClose,
  onConfirm,
  selectedTargetInfo,
  selectedTarget,
  updateFiles,
  updateMetadata,
  updatePreview,
  contentSourcePath,
  stagingPath,
  vdfPath,
  previewFilePath,
  metadataId,
  username,
  changenoteLength,
}) => {
  return (
    <Dialog
      open={open}
      onClose={() => !isPushing && onClose()}
      maxWidth="md"
      fullWidth
    >
      <DialogTitle sx={{ fontWeight: 900 }}>Confirm Workshop Upload</DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Alert severity="info">
            Review exactly what will be uploaded to Steam before continuing.
          </Alert>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 900, mb: 1 }}>Target Project</Typography>
            <Typography variant="body2">{selectedTargetInfo?.name || selectedTarget}</Typography>
            <Typography variant="caption" color="text.secondary">Root: {selectedTargetInfo?.path || 'Unknown project path'}</Typography>
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 900, mb: 1 }}>Upload Plan</Typography>
            <List dense disablePadding>
              <ListItem disableGutters>
                <ListItemText
                  primary={updateFiles ? 'Files & Binaries: WILL UPLOAD' : 'Files & Binaries: SKIPPED'}
                  secondary={updateFiles
                    ? `Copies from ${contentSourcePath} to ${stagingPath}, then uploads staging as contentfolder.`
                    : `No file staging step. SteamCMD will still use contentfolder path: ${stagingPath}.`}
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary={updateMetadata ? 'Workshop Metadata: WILL UPDATE' : 'Workshop Metadata: SKIPPED'}
                  secondary={updateMetadata
                    ? `Title, Description, Tags, Visibility, and changenote will be written into ${vdfPath}.`
                    : 'Title, Description, Tags, and Visibility will not be changed in this upload.'}
                />
              </ListItem>
              <ListItem disableGutters>
                <ListItemText
                  primary={updatePreview ? 'Poster Image: WILL UPDATE' : 'Poster Image: SKIPPED'}
                  secondary={updatePreview
                    ? `Preview image path in VDF: ${previewFilePath}`
                    : 'No preview image path will be included in VDF.'}
                />
              </ListItem>
            </List>
          </Paper>

          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 900, mb: 1 }}>Request Summary</Typography>
            <Stack spacing={0.5}>
              <Typography variant="body2">Workshop ID: {metadataId || 'Not set'}</Typography>
              <Typography variant="body2">Steam User: {username || 'Not set'}</Typography>
              <Typography variant="body2">Changenote length: {changenoteLength || 0} chars</Typography>
            </Stack>
          </Paper>
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPushing}>Cancel</Button>
        <Button
          variant="contained"
          onClick={onConfirm}
          disabled={isPushing}
        >
          {isPushing ? 'PUSHING...' : 'Confirm & Push'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default WorkshopPublishConfirmDialog;