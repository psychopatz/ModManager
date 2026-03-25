import React, { useState, useEffect } from 'react';
import { 
    Table, 
    TableBody, 
    TableCell, 
    TableContainer, 
    TableHead, 
    TableRow, 
    Paper,
    TablePagination, 
    Link, 
    Chip, 
    TextField, 
    InputAdornment, 
    Box,
    Typography,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Grid,
    Autocomplete
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { getItems, getTags } from '../services/api';

const ItemTable = () => {
    const [items, setItems] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);
    const [search, setSearch] = useState('');
    const [statusFilter, setStatusFilter] = useState('');
    const [tagFilter, setTagFilter] = useState(null);
    const [availableTags, setAvailableTags] = useState([]);
    const [minWeight, setMinWeight] = useState('');
    const [maxWeight, setMaxWeight] = useState('');
    const [minPrice, setMinPrice] = useState('');
    const [maxPrice, setMaxPrice] = useState('');

    const fetchItems = async () => {
        try {
            const response = await getItems({
                limit: rowsPerPage,
                offset: page * rowsPerPage,
                search: search || undefined,
                status: statusFilter || undefined,
                tag: tagFilter || undefined,
                min_weight: minWeight !== '' ? Number(minWeight) : undefined,
                max_weight: maxWeight !== '' ? Number(maxWeight) : undefined,
                min_price: minPrice !== '' ? Number(minPrice) : undefined,
                max_price: maxPrice !== '' ? Number(maxPrice) : undefined,
            });
            if (response.data && response.data.items) {
                setItems(response.data.items);
                setTotal(response.data.total || 0);
            } else {
                setItems([]);
                setTotal(0);
            }
        } catch (err) {
            console.error("Fetch error:", err);
            setItems([]);
            setTotal(0);
        }
    };

    const fetchTags = async () => {
        try {
            const response = await getTags();
            if (response.data && response.data.tags) {
                setAvailableTags(response.data.tags);
            }
        } catch (err) {
            console.error('Failed to fetch tags:', err);
        }
    };

    useEffect(() => {
        fetchTags();
    }, []);

    useEffect(() => {
        const timer = setTimeout(() => {
            fetchItems();
        }, 300); // Debounce search
        return () => clearTimeout(timer);
    }, [page, rowsPerPage, search, statusFilter, tagFilter, minWeight, maxWeight, minPrice, maxPrice]);

    const handleChangePage = (event, newPage) => {
        setPage(newPage);
    };

    const handleChangeRowsPerPage = (event) => {
        setRowsPerPage(parseInt(event.target.value, 10));
        setPage(0);
    };

    const handleSearchChange = (event) => {
        setSearch(event.target.value);
        setPage(0);
    };

    const getTagColor = (tag) => {
        if (tag.startsWith('Rarity.Common')) return 'default';
        if (tag.startsWith('Rarity.Uncommon')) return 'primary';
        if (tag.startsWith('Rarity.Rare')) return 'secondary';
        if (tag.startsWith('Rarity.Legendary')) return 'warning';
        if (tag.startsWith('Quality.Broken')) return 'error';
        return 'default';
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid item xs={12} sm={6} md={3} lg={2} xl={2}>
                        <TextField
                            fullWidth
                            size="small"
                            variant="outlined"
                            placeholder="Search names/IDs..."
                            value={search}
                            onChange={handleSearchChange}
                            InputProps={{
                                startAdornment: (
                                    <InputAdornment position="start">
                                        <SearchIcon />
                                    </InputAdornment>
                                ),
                            }}
                        />
                    </Grid>
                    <Grid item xs={6} sm={6} md={2} lg={2} xl={2}>
                        <FormControl fullWidth size="small">
                            <InputLabel>Status</InputLabel>
                            <Select
                                value={statusFilter}
                                label="Status"
                                onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
                            >
                                <MenuItem value="">All Statuses</MenuItem>
                                <MenuItem value="registered">Registered</MenuItem>
                                <MenuItem value="unregistered">Unregistered</MenuItem>
                                <MenuItem value="blacklisted">Blacklisted</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid item xs={6} sm={12} md={3} lg={3} xl={4}>
                        <Autocomplete
                            fullWidth
                            freeSolo
                            size="small"
                            options={availableTags}
                            value={tagFilter}
                            onChange={(event, newValue) => { setTagFilter(newValue); setPage(0); }}
                            onInputChange={(event, newInputValue) => { setTagFilter(newInputValue); setPage(0); }}
                            renderInput={(params) => (
                                <TextField {...params} label="Filter by Tag" variant="outlined" />
                            )}
                        />
                    </Grid>
                    <Grid item xs={6} sm={3} md={1} lg={1} xl={1}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Min Wt(kg)"
                            type="number"
                            value={minWeight}
                            onChange={(e) => { setMinWeight(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid item xs={6} sm={3} md={1} lg={1} xl={1}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Max Wt(kg)"
                            type="number"
                            value={maxWeight}
                            onChange={(e) => { setMaxWeight(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid item xs={6} sm={3} md={1} lg={1} xl={1}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Min Price($)"
                            type="number"
                            value={minPrice}
                            onChange={(e) => { setMinPrice(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid item xs={6} sm={3} md={1} lg={1} xl={1}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Max Price($)"
                            type="number"
                            value={maxPrice}
                            onChange={(e) => { setMaxPrice(e.target.value); setPage(0); }}
                        />
                    </Grid>
                </Grid>
            </Box>
            <TableContainer component={Paper} sx={{ flexGrow: 1, overflow: 'auto', boxShadow: 'none' }}>
                <Table size="small" stickyHeader>
                    <TableHead>
                        <TableRow>
                            <TableCell sx={{ fontWeight: 'bold' }}>Item ID</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Display Name</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Price</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Weight</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Tags</TableCell>
                            <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {items.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={6} align="center" sx={{ py: 3 }}>
                                    <Typography color="textSecondary">No items found</Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            items.map((item) => (
                                <TableRow key={item.id} hover>
                                    <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{item.id}</TableCell>
                                    <TableCell>{item.name}</TableCell>
                                    <TableCell>${item.price}</TableCell>
                                    <TableCell>{item.weight}kg</TableCell>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                            {item.tags?.map(tag => (
                                                <Chip 
                                                    key={tag} 
                                                    label={tag} 
                                                    size="small" 
                                                    variant="outlined"
                                                    color={getTagColor(tag)}
                                                    sx={{ fontSize: '0.65rem', height: 20 }}
                                                />
                                            ))}
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        {item.is_blacklisted ? (
                                            <Chip label="Blacklisted" size="small" color="error" variant="soft" />
                                        ) : item.is_registered ? (
                                            <Chip label="Registered" size="small" color="success" variant="soft" />
                                        ) : (
                                            <Chip label="Unregistered" size="small" color="warning" variant="soft" />
                                        )}
                                    </TableCell>
                                </TableRow>
                            ))
                        )}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                rowsPerPageOptions={[5, 10, 25, 50, 100]}
                component="div"
                count={total}
                rowsPerPage={rowsPerPage}
                page={page}
                onPageChange={handleChangePage}
                onRowsPerPageChange={handleChangeRowsPerPage}
            />
        </Box>
    );
};

export default ItemTable;
