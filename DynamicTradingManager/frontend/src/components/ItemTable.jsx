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
    Autocomplete,
    Button,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Stack,
    Alert
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { getItems, getTags, getOverrides, saveItemOverride, deleteItemOverride, addBlacklistItem, addWhitelistItem, deleteWhitelistItem } from '../services/api';

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
    const [overridesByItem, setOverridesByItem] = useState({});
    const [editingItem, setEditingItem] = useState(null);
    const [overrideDraft, setOverrideDraft] = useState({ basePrice: '', stockMin: '', stockMax: '', tags: [] });
    const [savingOverride, setSavingOverride] = useState(false);
    const [blacklistingItemId, setBlacklistingItemId] = useState('');
    const [whitelistMutatingItemId, setWhitelistMutatingItemId] = useState('');
    const [actionStatus, setActionStatus] = useState({ type: '', message: '' });

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

    const fetchOverrides = async () => {
        try {
            const response = await getOverrides();
            setOverridesByItem(response.data?.by_item || {});
        } catch (err) {
            console.error('Failed to fetch overrides:', err);
            setOverridesByItem({});
        }
    };

    useEffect(() => {
        fetchTags();
        fetchOverrides();
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

    const openOverrideEditor = (item) => {
        const existing = overridesByItem[item.id] || {};
        setEditingItem(item);
        setOverrideDraft({
            basePrice: existing.basePrice ?? '',
            stockMin: existing.stockRange?.min ?? '',
            stockMax: existing.stockRange?.max ?? '',
            tags: Array.isArray(existing.tags) ? existing.tags : [],
        });
        setActionStatus({ type: '', message: '' });
    };

    const closeOverrideEditor = () => {
        setEditingItem(null);
        setOverrideDraft({ basePrice: '', stockMin: '', stockMax: '', tags: [] });
    };

    const refreshData = async () => {
        await Promise.all([fetchItems(), fetchOverrides()]);
    };

    const handleSaveOverride = async () => {
        if (!editingItem) {
            return;
        }

        const payload = {
            item_id: editingItem.id,
        };

        if (overrideDraft.basePrice !== '') {
            const value = Number(overrideDraft.basePrice);
            if (!Number.isFinite(value) || value < 0) {
                setActionStatus({ type: 'error', message: 'Override price must be a non-negative number.' });
                return;
            }
            payload.base_price = value;
        }

        if (overrideDraft.stockMin !== '') {
            const value = Number(overrideDraft.stockMin);
            if (!Number.isInteger(value) || value < 0) {
                setActionStatus({ type: 'error', message: 'Stock min must be a non-negative integer.' });
                return;
            }
            payload.stock_min = value;
        }

        if (overrideDraft.stockMax !== '') {
            const value = Number(overrideDraft.stockMax);
            if (!Number.isInteger(value) || value < 0) {
                setActionStatus({ type: 'error', message: 'Stock max must be a non-negative integer.' });
                return;
            }
            payload.stock_max = value;
        }

        if (
            payload.stock_min !== undefined
            && payload.stock_max !== undefined
            && payload.stock_min > payload.stock_max
        ) {
            setActionStatus({ type: 'error', message: 'Stock min cannot be greater than stock max.' });
            return;
        }

        if ((overrideDraft.tags || []).length > 0) {
            payload.tags = overrideDraft.tags;
        }

        if (
            payload.base_price === undefined
            && payload.stock_min === undefined
            && payload.stock_max === undefined
            && payload.tags === undefined
        ) {
            setActionStatus({ type: 'error', message: 'Set at least one override field before saving.' });
            return;
        }

        setSavingOverride(true);
        try {
            await saveItemOverride(payload);
            await refreshData();
            setActionStatus({ type: 'success', message: `Saved override for ${editingItem.id}.` });
            closeOverrideEditor();
        } catch (err) {
            setActionStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to save override.' });
        } finally {
            setSavingOverride(false);
        }
    };

    const handleDeleteOverride = async (itemId) => {
        setSavingOverride(true);
        try {
            await deleteItemOverride(itemId);
            await refreshData();
            setActionStatus({ type: 'success', message: `Deleted override for ${itemId}.` });
            if (editingItem?.id === itemId) {
                closeOverrideEditor();
            }
        } catch (err) {
            setActionStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to delete override.' });
        } finally {
            setSavingOverride(false);
        }
    };

    const handleBlacklist = async (itemId) => {
        setBlacklistingItemId(itemId);
        try {
            await addBlacklistItem(itemId);
            await refreshData();
            setActionStatus({ type: 'success', message: `${itemId} added to blacklist.` });
        } catch (err) {
            setActionStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to add item to blacklist.' });
        } finally {
            setBlacklistingItemId('');
        }
    };

    const handleWhitelist = async (item) => {
        setWhitelistMutatingItemId(item.id);
        try {
            if (item.is_whitelisted) {
                await deleteWhitelistItem(item.id);
                setActionStatus({ type: 'success', message: `${item.id} removed from whitelist.` });
            } else {
                await addWhitelistItem(item.id);
                setActionStatus({ type: 'success', message: `${item.id} added to whitelist.` });
            }
            await refreshData();
        } catch (err) {
            setActionStatus({ type: 'error', message: err?.response?.data?.detail || 'Failed to update whitelist.' });
        } finally {
            setWhitelistMutatingItemId('');
        }
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
            {actionStatus.message ? (
                <Alert
                    severity={actionStatus.type || 'info'}
                    onClose={() => setActionStatus({ type: '', message: '' })}
                    sx={{ mb: 1 }}
                >
                    {actionStatus.message}
                </Alert>
            ) : null}
            <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                <Grid container spacing={2} alignItems="center">
                    <Grid size={{ xs: 12, sm: 6, md: 3, lg: 2, xl: 2 }}>
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
                    <Grid size={{ xs: 6, sm: 6, md: 2, lg: 2, xl: 2 }}>
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
                                <MenuItem value="whitelisted">Whitelisted</MenuItem>
                            </Select>
                        </FormControl>
                    </Grid>
                    <Grid size={{ xs: 6, sm: 12, md: 3, lg: 3, xl: 4 }}>
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
                    <Grid size={{ xs: 6, sm: 3, md: 1, lg: 1, xl: 1 }}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Min Wt(kg)"
                            type="number"
                            value={minWeight}
                            onChange={(e) => { setMinWeight(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid size={{ xs: 6, sm: 3, md: 1, lg: 1, xl: 1 }}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Max Wt(kg)"
                            type="number"
                            value={maxWeight}
                            onChange={(e) => { setMaxWeight(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid size={{ xs: 6, sm: 3, md: 1, lg: 1, xl: 1 }}>
                        <TextField
                            fullWidth
                            size="small"
                            label="Min Price($)"
                            type="number"
                            value={minPrice}
                            onChange={(e) => { setMinPrice(e.target.value); setPage(0); }}
                        />
                    </Grid>
                    <Grid size={{ xs: 6, sm: 3, md: 1, lg: 1, xl: 1 }}>
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
                            <TableCell sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {items.length === 0 ? (
                            <TableRow>
                                <TableCell colSpan={7} align="center" sx={{ py: 3 }}>
                                    <Typography color="textSecondary">No items found</Typography>
                                </TableCell>
                            </TableRow>
                        ) : (
                            items.map((item) => (
                                <TableRow key={item.id} hover>
                                    {/** keep per-item actions visible for quick override management */}
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
                                        ) : item.is_whitelisted ? (
                                            <Chip label="Whitelisted" size="small" color="info" variant="soft" />
                                        ) : item.is_registered ? (
                                            <Chip label="Registered" size="small" color="success" variant="soft" />
                                        ) : (
                                            <Chip label="Unregistered" size="small" color="warning" variant="soft" />
                                        )}
                                    </TableCell>
                                    <TableCell>
                                        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                color="error"
                                                onClick={() => handleBlacklist(item.id)}
                                                disabled={item.is_blacklisted || blacklistingItemId === item.id}
                                            >
                                                {blacklistingItemId === item.id ? 'Blacklisting...' : item.is_blacklisted ? 'Blacklisted' : 'Blacklist'}
                                            </Button>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                color={item.is_whitelisted ? 'warning' : 'info'}
                                                onClick={() => handleWhitelist(item)}
                                                disabled={whitelistMutatingItemId === item.id}
                                            >
                                                {whitelistMutatingItemId === item.id
                                                    ? (item.is_whitelisted ? 'Removing...' : 'Whitelisting...')
                                                    : (item.is_whitelisted ? 'Remove Whitelist' : 'Whitelist')}
                                            </Button>
                                            <Button
                                                variant="outlined"
                                                size="small"
                                                onClick={() => openOverrideEditor(item)}
                                            >
                                                Edit Override
                                            </Button>
                                            {overridesByItem[item.id] ? (
                                                <Button
                                                    variant="outlined"
                                                    size="small"
                                                    onClick={() => handleDeleteOverride(item.id)}
                                                    disabled={savingOverride}
                                                >
                                                    Delete Override
                                                </Button>
                                            ) : null}
                                        </Stack>
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

            <Dialog open={Boolean(editingItem)} onClose={closeOverrideEditor} fullWidth maxWidth="md">
                <DialogTitle>
                    Edit Item Override {editingItem ? `- ${editingItem.id}` : ''}
                </DialogTitle>
                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 0.5 }}>
                        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
                            <TextField
                                label="Override Price"
                                type="number"
                                value={overrideDraft.basePrice}
                                onChange={(event) => setOverrideDraft((current) => ({ ...current, basePrice: event.target.value }))}
                                fullWidth
                            />
                            <TextField
                                label="Stock Min"
                                type="number"
                                value={overrideDraft.stockMin}
                                onChange={(event) => setOverrideDraft((current) => ({ ...current, stockMin: event.target.value }))}
                                fullWidth
                            />
                            <TextField
                                label="Stock Max"
                                type="number"
                                value={overrideDraft.stockMax}
                                onChange={(event) => setOverrideDraft((current) => ({ ...current, stockMax: event.target.value }))}
                                fullWidth
                            />
                        </Stack>

                        <Autocomplete
                            multiple
                            options={availableTags}
                            value={overrideDraft.tags}
                            onChange={(_, newValue) => setOverrideDraft((current) => ({ ...current, tags: newValue }))}
                            renderInput={(params) => (
                                <TextField
                                    {...params}
                                    label="Override Tags"
                                    placeholder="Pick tags"
                                />
                            )}
                        />
                    </Stack>
                </DialogContent>
                <DialogActions>
                    <Button onClick={closeOverrideEditor} disabled={savingOverride}>Cancel</Button>
                    <Button
                        onClick={() => setOverrideDraft((current) => ({ ...current, tags: [] }))}
                        disabled={savingOverride}
                    >
                        Clear Tag Override
                    </Button>
                    <Button onClick={handleSaveOverride} variant="contained" disabled={savingOverride}>
                        {savingOverride ? 'Saving...' : 'Save Override'}
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    );
};

export default ItemTable;
