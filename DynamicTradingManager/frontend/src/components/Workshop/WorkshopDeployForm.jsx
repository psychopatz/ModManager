import React from 'react';
import {
  Box,
  Button,
  IconButton,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  VisibilityOff,
} from '@mui/icons-material';
import BBCodeEditorPreview from '../Common/BBCodeEditorPreview';

const WorkshopDeployForm = ({
  latestStage3Batch,
  changenote,
  setChangenote,
  setSnackbar,
  username,
  setUsername,
  password,
  setPassword,
  showPassword,
  setShowPassword,
  steamGuardCode,
  setSteamGuardCode,
  onPushSubmit,
  canSubmit,
}) => {
  return (
    <form onSubmit={onPushSubmit}>
      <Stack spacing={3}>
        <Box>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 800 }}>Workshop Changenote (BBCode)</Typography>
            <Button
              size="small"
              variant="outlined"
              disabled={!latestStage3Batch?.workshopMetadata}
              onClick={() => {
                const latest = String(latestStage3Batch?.workshopMetadata || '').trim();
                if (!latest) return;
                setChangenote(latest);
                const batchLabel = latestStage3Batch?.modName || latestStage3Batch?.module || latestStage3Batch?.id || 'Stage 3';
                setSnackbar({ open: true, message: `Loaded Stage 3 output from '${batchLabel}'.`, severity: 'success' });
              }}
            >
              {latestStage3Batch?.workshopMetadata
                ? `Use Stage 3 - ${latestStage3Batch.modName || latestStage3Batch.module || latestStage3Batch.id}`
                : 'Use Latest Stage 3'}
            </Button>
          </Stack>
          <BBCodeEditorPreview
            label="Workshop Changenote"
            value={changenote}
            onChange={setChangenote}
            editable
            minRows={6}
            maxRows={26}
            editorHelperText={latestStage3Batch?.workshopMetadata
              ? `Auto-source available from batch ${latestStage3Batch.id}. This is sent to Steam as changenote.`
              : 'This is sent to Steam as the update note for this publish.'}
            previewTitle="Rendered Changenote Preview"
          />
        </Box>
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
          InputProps={{
            endAdornment: (
              <IconButton onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? <VisibilityOff /> : <VisibilityIcon />}
              </IconButton>
            ),
          }}
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
          data-testid="workshop-publish-button"
          disabled={!canSubmit}
          sx={{ py: 2.5, borderRadius: 4, fontWeight: 900 }}
        >
          PUSH UPDATE TO STEAM
        </Button>
      </Stack>
    </form>
  );
};

export default WorkshopDeployForm;