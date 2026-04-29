import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Fab,
  Tooltip,
  IconButton,
  TextField,
  Avatar,
  Stack,
  Paper,
  Divider,
  Collapse,
  Button,
  Zoom,
  Fade,
  Dialog,
  DialogContent,
  DialogTitle,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  FormControlLabel,
  Checkbox,
  Grid,
  Select,
  MenuItem,
  InputLabel,
  FormControl
} from '@mui/material';
import {
  SmartToy as AiIcon,
  Close as CloseIcon,
  DeleteOutline as ClearIcon,
  Send as SendIcon,
  AutoAwesome as MagicIcon,
  Tune as SystemPromptIcon,
  ExpandMore as ExpandIcon,
  Edit as EditIcon,
  Refresh as RerunIcon,
  Check as SaveIcon,
  Person as UserIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useLLM } from '../../hooks/useLLM';
import { useLLMInternal } from '../../context/LLMContext';
import { isReasoningEffortSupported } from '../../utils/llmUtils';
import * as api from '../../services/api';

const SYSTEM_PROMPT_KEY = 'dt_chat_system_prompt';
const DEFAULT_SYSTEM_PROMPT = "You are a professional AI Assistant for Project Zomboid Mod Management. Help the user with modding, code analysis, and configuration.";

const TypingAnimation = () => (
  <Box sx={{ display: 'flex', gap: 0.5, p: 1, alignItems: 'center', height: 20 }}>
    {[0, 1, 2].map((i) => (
      <Box
        key={i}
        sx={{
          width: 6,
          height: 6,
          bgcolor: 'primary.main',
          borderRadius: '50%',
          animation: 'bounce 1.4s infinite ease-in-out both',
          animationDelay: `${i * 0.16}s`,
          '@keyframes bounce': {
            '0%, 80%, 100%': { transform: 'scale(0)' },
            '40%': { transform: 'scale(1)' },
          },
        }}
      />
    ))}
  </Box>
);

const LLMChatFloating = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [editingIndex, setEditingIndex] = useState(null);
  const [editInput, setEditInput] = useState('');
  const [showSystemPrompt, setShowSystemPrompt] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState(() => {
    return localStorage.getItem(SYSTEM_PROMPT_KEY) || DEFAULT_SYSTEM_PROMPT;
  });
  
  const { streamChat, config } = useLLM();
  const { setConfig, setSettingsOpen } = useLLMInternal();
  const scrollRef = useRef(null);
  const activeProviderId = config.activeProvider;
  const activeProvider = config.providers[activeProviderId] || {};

  useEffect(() => {
    localStorage.setItem(SYSTEM_PROMPT_KEY, systemPrompt);
  }, [systemPrompt]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping]);

  const handleModelChange = (modelId) => {
    setSettingsOpen(true);
  };

  const parseThinking = (text) => {
    if (!text) return [ '', null ];
    const thinkRegex = /<think>([\s\S]*?)<\/think>/i;
    const match = text.match(thinkRegex);
    if (match) {
      const clean = text.replace(thinkRegex, '').trim();
      return [ clean, match[1].trim() ];
    }
    return [ text, null ];
  };

  const executeChat = async (history) => {
    setIsTyping(true);
    const assistantMsgIndex = history.length;
    setMessages([...history, { role: 'assistant', content: '', thinking: '', isStreaming: true }]);

    try {
      await streamChat(history, {
        systemPrompt,
        thinking: isThinking,
        reasoningEffort: config.reasoningEffort,
        onChunk: (chunk) => {
          setMessages((prev) => {
            const next = [...prev];
            const msg = { ...next[assistantMsgIndex] };
            msg.content += chunk.content || '';
            msg.thinking += chunk.thinking || '';
            if (chunk.model) msg.model = chunk.model;
            next[assistantMsgIndex] = msg;
            return next;
          });
        }
      });
      
      setMessages((prev) => {
        const next = [...prev];
        if (next[assistantMsgIndex]) {
          next[assistantMsgIndex].isStreaming = false;
        }
        return next;
      });
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: 'system', content: `Error: ${error.message}` },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isTyping) return;
    const userMessage = { role: 'user', content: input };
    const newHistory = [...messages, userMessage];
    setMessages(newHistory);
    setInput('');
    await executeChat(newHistory);
  };

  const handleEdit = (index) => {
    setEditingIndex(index);
    setEditInput(messages[index].content);
  };

  const handleSaveEdit = async (index) => {
    if (!editInput.trim()) { setEditingIndex(null); return; }
    const truncatedHistory = messages.slice(0, index);
    const updatedUserMsg = { role: 'user', content: editInput };
    const newHistory = [...truncatedHistory, updatedUserMsg];
    setMessages(newHistory);
    setEditingIndex(null);
    await executeChat(newHistory);
  };

  const handleRerun = async (index) => {
    const truncatedHistory = messages.slice(0, index + 1);
    setMessages(truncatedHistory);
    await executeChat(truncatedHistory);
  };

  const handleClear = () => {
    setMessages([]);
    setEditingIndex(null);
  };

  const handleResetSystemPrompt = () => {
    setSystemPrompt(DEFAULT_SYSTEM_PROMPT);
  };

  if (!isOpen) {
    return (
      <Box sx={{ position: 'fixed', bottom: 100, right: 32, zIndex: 9999, pointerEvents: 'auto' }}>
        <Zoom in={!isOpen}>
          <Tooltip title={`AI Chat (${activeProvider.label || activeProvider.id})`} placement="left">
            <Fab 
              color="primary" 
              onClick={() => setIsOpen(true)} 
              size="medium"
              sx={{ boxShadow: '0 8px 32px rgba(0,0,0,0.4)', pointerEvents: 'auto' }}
            >
              <AiIcon />
            </Fab>
          </Tooltip>
        </Zoom>
      </Box>
    );
  }

  return (
    <Dialog 
        open={isOpen} 
        onClose={() => setIsOpen(false)}
        maxWidth="md"
        fullWidth
        TransitionComponent={Fade}
        PaperProps={{
            sx: {
                height: '80vh',
                borderRadius: 5,
                overflow: 'hidden',
                bgcolor: '#09090b', 
                border: '1px solid rgba(255,255,255,0.1)',
                boxShadow: '0 24px 48px rgba(0,0,0,0.5)',
            }
        }}
    >
      <DialogTitle
        component="div"
        sx={{
          p: 2.5,
          bgcolor: 'rgba(255,255,255,0.03)',
          backdropFilter: 'blur(10px)',
          color: 'white',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          zIndex: 10
        }}
      >
        <Stack direction="row" spacing={1.5} alignItems="center">
          <Avatar sx={{ bgcolor: 'primary.main', width: 32, height: 32 }}>
            <AiIcon sx={{ fontSize: 20 }} />
          </Avatar>
          <Box>
            <Typography component="div" sx={{ fontSize: '1rem', fontWeight: 800, color: 'white', lineHeight: 1.2 }}>
              AI Assistant
            </Typography>
            <Typography component="div" variant="caption" sx={{ color: 'text.secondary', fontWeight: 500 }}>
              {activeProvider.label} • {activeProvider.model || 'Auto'}
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" spacing={0.5}>
          <Tooltip title="Configure System Prompt & Mode">
            <IconButton 
              size="small" 
              sx={{ color: showSystemPrompt ? 'primary.main' : 'text.secondary' }} 
              onClick={() => setShowSystemPrompt(!showSystemPrompt)}
            >
              <SystemPromptIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <Tooltip title="Clear chat history">
            <IconButton size="small" sx={{ color: 'text.secondary' }} onClick={handleClear}>
              <ClearIcon fontSize="small" />
            </IconButton>
          </Tooltip>
          <IconButton size="small" sx={{ color: 'text.secondary' }} onClick={() => setIsOpen(false)}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </Stack>
      </DialogTitle>

      <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* System Prompt & Mode Editor */}
        <Collapse in={showSystemPrompt}>
          <Box sx={{ p: 2.5, bgcolor: 'rgba(255,255,255,0.02)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <Stack spacing={2.5}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="caption" fontWeight={700} color="primary" sx={{ textTransform: 'uppercase', letterSpacing: 1 }}>
                  Configuration & Personality
                </Typography>
                <Stack direction="row" spacing={2} alignItems="center">
                  <FormControlLabel
                    control={
                      <Checkbox
                        size="small"
                        checked={isThinking}
                        onChange={(e) => setIsThinking(e.target.checked)}
                        sx={{ color: 'primary.main', '&.Mui-checked': { color: 'primary.main' } }}
                      />
                    }
                    label={
                      <Typography variant="caption" sx={{ color: 'text.primary', fontWeight: 600 }}>
                        Thinking Mode
                      </Typography>
                    }
                  />
                  {isThinking && isReasoningEffortSupported(activeProvider.model, activeProvider.base_url) && (
                    <FormControl size="small" sx={{ minWidth: 100 }}>
                      <InputLabel id="reasoning-effort-label" sx={{ fontSize: '0.7rem' }}>Effort</InputLabel>
                      <Select
                        labelId="reasoning-effort-label"
                        label="Effort"
                        value={config.reasoningEffort || 'medium'}
                        onChange={(e) => setConfig(prev => ({ ...prev, reasoningEffort: e.target.value }))}
                        sx={{ height: 28, fontSize: '0.75rem' }}
                      >
                        <MenuItem value="low" sx={{ fontSize: '0.75rem' }}>Low</MenuItem>
                        <MenuItem value="medium" sx={{ fontSize: '0.75rem' }}>Medium</MenuItem>
                        <MenuItem value="high" sx={{ fontSize: '0.75rem' }}>High</MenuItem>
                      </Select>
                    </FormControl>
                  )}
                </Stack>
              </Stack>

              <Box sx={{ p: 2, borderRadius: 2, bgcolor: 'rgba(25, 118, 210, 0.05)', border: '1px dashed rgba(25, 118, 210, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <Box>
                    <Typography variant="body2" sx={{ fontWeight: 700, color: 'text.primary' }}>
                        {activeProvider.model || 'No model selected'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                        Active Provider: {activeProvider.label || activeProvider.id}
                    </Typography>
                </Box>
                <Button 
                    size="small" 
                    variant="contained" 
                    startIcon={<SettingsIcon />} 
                    onClick={() => setSettingsOpen(true)}
                    sx={{ textTransform: 'none', borderRadius: 2 }}
                >
                    Change Model
                </Button>
              </Box>

              <Box>
                <Typography variant="caption" display="block" gutterBottom sx={{ fontWeight: 600, color: 'text.secondary' }}>
                  System Prompt (AI Identity)
                </Typography>
                <TextField
                  fullWidth
                  multiline
                  maxRows={4}
                  size="small"
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  sx={{ 
                    '& .MuiInputBase-root': { 
                      fontSize: '0.8rem', 
                      color: 'text.secondary',
                      bgcolor: 'rgba(0,0,0,0.2)' 
                    } 
                  }}
                />
              </Box>

              <Stack direction="row" spacing={1} justifyContent="flex-end">
                <Button size="small" variant="text" sx={{ color: 'text.secondary' }} onClick={handleResetSystemPrompt}>Reset to Default</Button>
                <Button size="small" variant="outlined" onClick={() => setShowSystemPrompt(false)}>Close Editor</Button>
              </Stack>
            </Stack>
          </Box>
        </Collapse>
        {/* Messages Container */}
        <Box
          ref={scrollRef}
          sx={{
            flex: 1,
            p: 3,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 4,
            scrollBehavior: 'smooth',
            '&::-webkit-scrollbar': { width: 6 },
            '&::-webkit-scrollbar-thumb': { bgcolor: 'rgba(255,255,255,0.1)', borderRadius: 3 }
          }}
        >
          {messages.length === 0 && (
            <Fade in={true} timeout={800}>
              <Box sx={{ mt: 12, textAlign: 'center' }}>
                <AiIcon sx={{ fontSize: 80, mb: 2, color: 'primary.main', opacity: 0.8 }} />
                <Typography variant="h5" fontWeight={900} sx={{ color: 'white', mb: 1 }}>How can I help you?</Typography>
                <Typography variant="body2" color="text.secondary">Ask me about modding, code, or general information.</Typography>
              </Box>
            </Fade>
          )}

          {messages.map((msg, i) => {
            const isUser = msg.role === 'user';
            const isSystem = msg.role === 'system';
            const [cleanContent, inlineThinking] = parseThinking(msg.content);
            const displayThinking = msg.thinking || inlineThinking;

            if (isSystem) {
                return (
                    <Box key={i} sx={{ alignSelf: 'center', width: '90%' }}>
                        <Paper color="error" sx={{ p: 1.5, bgcolor: 'rgba(239, 68, 68, 0.05)', border: '1px solid rgba(239, 68, 68, 0.2)', textAlign: 'center', borderRadius: 2 }}>
                            <Typography variant="caption" color="error">{msg.content}</Typography>
                        </Paper>
                    </Box>
                );
            }

            return (
              <Box
                key={i}
                sx={{
                  alignSelf: isUser ? 'flex-end' : 'flex-start',
                  maxWidth: isUser ? '85%' : '92%',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 1.5,
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, flexDirection: isUser ? 'row-reverse' : 'row' }}>
                  <Avatar 
                    sx={{ 
                        width: 30, 
                        height: 30, 
                        bgcolor: isUser ? 'primary.main' : 'rgba(255,255,255,0.05)',
                        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.1)',
                        boxShadow: isUser ? '0 4px 12px rgba(25, 118, 210, 0.3)' : 'none'
                    }}
                  >
                    {isUser ? <UserIcon sx={{ fontSize: 18 }} /> : <AiIcon sx={{ fontSize: 18 }} />}
                  </Avatar>
                  
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', gap: 0.5 }}>
                    <Paper
                      elevation={0}
                      sx={{
                        p: 2,
                        borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                        background: isUser ? 'linear-gradient(135deg, #1976d2 0%, #1565c0 100%)' : 'rgba(255,255,255,0.03)',
                        color: 'white',
                        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        position: 'relative',
                        boxShadow: isUser ? '0 4px 15px rgba(0,0,0,0.2)' : 'none',
                        '&:hover .msg-actions': { opacity: 1 }
                      }}
                    >
                        {editingIndex === i ? (
                            <Box sx={{ minWidth: 280 }}>
                                <TextField
                                    fullWidth
                                    multiline
                                    size="small"
                                    value={editInput}
                                    onChange={(e) => setEditInput(e.target.value)}
                                    autoFocus
                                    sx={{ 
                                        mb: 1.5, 
                                        '& .MuiInputBase-root': { color: 'white', bgcolor: 'rgba(0,0,0,0.2)' } 
                                    }}
                                />
                                <Stack direction="row" spacing={1} justifyContent="flex-end">
                                    <Button size="small" sx={{ color: 'text.secondary' }} onClick={() => setEditingIndex(null)}>Cancel</Button>
                                    <Button size="small" variant="contained" color="primary" onClick={() => handleSaveEdit(i)}>Update & Rerun</Button>
                                </Stack>
                            </Box>
                        ) : (
                            <>
                                <Box sx={{ 
                                    whiteSpace: 'pre-wrap', 
                                    wordBreak: 'break-word', 
                                    lineHeight: 1.8, 
                                    fontWeight: 400,
                                    fontSize: '0.925rem'
                                }}>
                                    {cleanContent || (!msg.thinking && msg.isStreaming && <TypingAnimation />)}
                                </Box>
                                
                                {/* Floating Actions */}
                                <Box 
                                    className="msg-actions"
                                    sx={{ 
                                        position: 'absolute', 
                                        top: -32, 
                                        [isUser ? 'right' : 'left']: 0,
                                        opacity: 0,
                                        transition: 'opacity 0.2s',
                                        display: 'flex',
                                        gap: 0.5,
                                        pointerEvents: 'auto'
                                    }}
                                >
                                    {isUser && (
                                        <IconButton size="small" sx={{ bgcolor: '#1e1e1e', boxShadow: 2, '&:hover': { bgcolor: '#2e2e2e' } }} onClick={() => handleEdit(i)}>
                                            <EditIcon sx={{ fontSize: 13, color: 'text.secondary' }} />
                                        </IconButton>
                                    )}
                                    {!isUser && !msg.isStreaming && i > 0 && (
                                        <IconButton size="small" sx={{ bgcolor: '#1e1e1e', boxShadow: 2, '&:hover': { bgcolor: '#2e2e2e' } }} onClick={() => handleRerun(i - 1)}>
                                            <RerunIcon sx={{ fontSize: 13, color: 'text.secondary' }} />
                                        </IconButton>
                                    )}
                                </Box>
                            </>
                        )}
                    </Paper>

                    {/* Thinking/Reasoning Display */}
                    {displayThinking && (
                        <Accordion
                            variant="outlined"
                            sx={{
                            width: '100%',
                            mt: 0.5,
                            bgcolor: 'rgba(255,255,255,0.02)',
                            border: 'none',
                            borderRadius: '12px !important',
                            '&:before': { display: 'none' },
                            }}
                        >
                            <AccordionSummary
                            expandIcon={<ExpandIcon sx={{ fontSize: 14, color: 'text.secondary' }} />}
                            sx={{ 
                                minHeight: 0, 
                                '& .MuiAccordionSummary-content': { my: 1, display: 'flex', alignItems: 'center', gap: 1 } 
                            }}
                            >
                            {msg.isStreaming && !cleanContent && <CircularProgress size={10} thickness={6} color="primary" />}
                            <Typography component="div" variant="caption" sx={{ fontWeight: 700, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 0.5, fontSize: '0.65rem' }}>
                                {msg.isStreaming && !cleanContent ? 'Analyzing Request...' : 'Reasoning Process'}
                            </Typography>
                            </AccordionSummary>
                            <AccordionDetails sx={{ pt: 0, pb: 2 }}>
                            <Typography
                                variant="caption"
                                sx={{
                                    display: 'block',
                                    fontSize: '0.75rem',
                                    color: 'text.secondary',
                                    fontStyle: 'italic',
                                    whiteSpace: 'pre-wrap',
                                    borderLeft: '2px solid rgba(255,255,255,0.1)',
                                    pl: 2,
                                    lineHeight: 1.6
                                }}
                            >
                                {displayThinking}
                            </Typography>
                            </AccordionDetails>
                        </Accordion>
                    )}
                  </Box>
                </Box>
              </Box>
            );
          })}

          {isTyping && messages.length > 0 && !messages[messages.length-1].isStreaming && (
            <Box sx={{ alignSelf: 'flex-start', ml: 6 }}>
              <TypingIndicator />
            </Box>
          )}
        </Box>

        {/* Input Area */}
        <Box 
            sx={{ 
                p: 3, 
                borderTop: '1px solid rgba(255,255,255,0.05)', 
                bgcolor: 'rgba(255,255,255,0.01)',
                backdropFilter: 'blur(5px)'
            }}
        >
          <Stack direction="row" spacing={1.5} alignItems="flex-end">
            <TextField
              fullWidth
              multiline
              maxRows={6}
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                  }
              }}
              autoComplete="off"
              sx={{ 
                  '& .MuiInputBase-root': { 
                      borderRadius: 4, 
                      px: 2, 
                      py: 1.5,
                      bgcolor: 'rgba(255,255,255,0.03)',
                      color: 'white',
                      border: '1px solid rgba(255,255,255,0.08)',
                      '&:hover': { border: '1px solid rgba(255,255,255,0.15)' },
                      '&.Mui-focused': { border: '1px solid #1976d2' }
                  },
                  '& .MuiOutlinedInput-notchedOutline': { border: 'none' }
              }}
            />
            <IconButton 
                color="primary" 
                onClick={handleSend} 
                disabled={!input.trim() || isTyping} 
                sx={{ 
                    bgcolor: 'primary.main', 
                    color: 'white',
                    width: 48,
                    height: 48,
                    borderRadius: 3.5,
                    boxShadow: '0 4px 12px rgba(25, 118, 210, 0.3)',
                    '&:hover': { bgcolor: 'primary.dark', transform: 'translateY(-2px)' },
                    '&.Mui-disabled': { bgcolor: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.2)', boxShadow: 'none' },
                    transition: 'all 0.2s'
                }}
            >
              <SendIcon fontSize="small" />
            </IconButton>
          </Stack>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default LLMChatFloating;
