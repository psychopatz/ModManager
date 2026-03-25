import React from 'react';
import { Typography, Paper, Box } from '@mui/material';
import ItemTable from './ItemTable';

const ItemsPage = () => {
    return (
        <Paper elevation={3} sx={{ p: 3, flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h4" gutterBottom>
                Vanilla Items Database
            </Typography>
            <Typography variant="body1" color="textSecondary" sx={{ mb: 2 }}>
                Browse, search, and filter all items available in the base game.
            </Typography>
            <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                <ItemTable />
            </Box>
        </Paper>
    );
};

export default ItemsPage;
