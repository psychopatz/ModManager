import React from 'react';
import { Typography, Paper, Box } from '@mui/material';
import ItemTable from './ItemTable';

const ItemsPage = () => {
    return (
        <Paper elevation={3} sx={{ p: 3, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h4" gutterBottom>
                Item Database
            </Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 2 }}>
                Browse, search, and filter all items, then quickly apply per-item override settings.
            </Typography>
            <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                <ItemTable />
            </Box>
        </Paper>
    );
};

export default ItemsPage;
