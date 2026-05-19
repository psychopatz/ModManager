import React from 'react';
import { Autocomplete, Box, Chip, TextField, Typography } from '@mui/material';

function TagCollectionEditor({
  label,
  helperText,
  values,
  options,
  onChange,
}) {
  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        {label}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.25 }}>
        {helperText}
      </Typography>
      <Autocomplete
        multiple
        freeSolo
        options={options}
        value={values}
        onChange={(_, nextValue) => onChange(nextValue)}
        renderTags={(tagValue, getTagProps) => tagValue.map((option, index) => (
          <Chip {...getTagProps({ index })} key={`${label}-${option}-${index}`} size="small" label={option} />
        ))}
        renderInput={(params) => <TextField {...params} label={label} placeholder="Type a tag or choose from autocomplete" />}
      />
    </Box>
  );
}

export default TagCollectionEditor;
