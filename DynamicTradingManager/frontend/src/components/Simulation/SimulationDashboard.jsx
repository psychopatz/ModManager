import React, { useState, useEffect, useMemo } from 'react';
import { 
  Box, Typography, Paper, CircularProgress, Alert, 
  Grid, Card, CardContent, Tabs, Tab, Table, TableBody, TableCell, 
  TableContainer, TableHead, TableRow, Chip, Button, TextField,
  MenuItem, Select, FormControl, InputLabel, Divider, List, ListItem,
  ListItemText, ListItemSecondaryAction, IconButton, InputAdornment
} from '@mui/material';
import { 
  Add as AddIcon, 
  Remove as RemoveIcon, 
  PlayArrow as PlayIcon, 
  RestartAlt as ResetIcon,
  ShoppingCart as CartIcon,
  Search as SearchIcon,
  ContentCopy as CopyIcon
} from '@mui/icons-material';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ChartTooltip, Legend, ResponsiveContainer
} from 'recharts';
import { getSimulationData } from '../../services/api';
import { dayToSeason, tagMatches, getEventPriceMult } from './simUtils';

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && (
        <Box sx={{ p: 3 }}>
          {children}
        </Box>
      )}
    </div>
  );
}

export default function SimulationDashboard() {
  const [baseData, setBaseData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [tabValue, setTabValue] = useState(0);

  // Simulation State
  const [day, setDay] = useState(0);
  const [activeFlash, setActiveFlash] = useState({}); // { eventId: expiresAtDay }
  const [lastFlashDay, setLastFlashDay] = useState(-10);
  
  // Trader Simulator State
  const [wallet, setWallet] = useState(1000);
  const [selectedTrader, setSelectedTrader] = useState('');
  const [inventory, setInventory] = useState({}); // { itemId: qty }
  const [forcedEvents, setForcedEvents] = useState([]);
  const [simSearch, setSimSearch] = useState('');
  const [localStock, setLocalStock] = useState({}); // Cloned stock for the current session

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await getSimulationData();
      setBaseData(response.data);
      // Initialize simulator with first archetype
      if (response.data.archetypes) {
        const firstArch = Object.keys(response.data.archetypes)[0];
        setSelectedTrader(firstArch || '');
        if (firstArch && response.data.day0.traderSamples[firstArch]) {
          setLocalStock(JSON.parse(JSON.stringify(response.data.day0.traderSamples[firstArch].stock)));
        }
      }
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to fetch simulation data. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  // Logic for computing active events based on current day
  const activeEventIds = useMemo(() => {
    if (!baseData) return [];
    const { events, config } = baseData;
    const currentSeason = dayToSeason(day);
    
    // 1. Meta/Seasonal events
    const active = new Set();
    Object.entries(events).forEach(([id, ev]) => {
      if (ev.event_type === 'meta' || ev.event_type === 'seasonal') {
        let pass = false;
        if (ev.condition_kind === 'none' || !ev.condition_kind) pass = true;
        else if (ev.condition_kind === 'season') pass = (currentSeason === ev.condition_value);
        else if (ev.condition_kind === 'nights_gt' || ev.condition_kind === 'days_gt') pass = (day > Number(ev.condition_value));
        
        if (pass) active.add(id);
      }
    });

    // 2. Active Flashes (still within expiry)
    Object.entries(activeFlash).forEach(([id, expiry]) => {
      if (day < expiry) active.add(id);
    });

    // 3. Forced Events
    forcedEvents.forEach(id => active.add(id));

    return Array.from(active).sort();
  }, [day, activeFlash, forcedEvents, baseData]);

  const activeEventDefs = useMemo(() => {
    if (!baseData) return [];
    return activeEventIds.map(id => baseData.events[id]).filter(Boolean);
  }, [activeEventIds, baseData]);

  // Advance Simulation
  const advanceDay = (days) => {
    let currentDay = day;
    let currentLastFlash = lastFlashDay;
    let currentFlashes = { ...activeFlash };

    for (let i = 0; i < days; i++) {
        currentDay += 1;
        // Clean expired
        Object.entries(currentFlashes).forEach(([id, expiry]) => {
            if (currentDay >= expiry) delete currentFlashes[id];
        });

        // Roll for new flashes
        const flashCandidates = Object.entries(baseData.events)
            .filter(([id, ev]) => ev.event_type === 'flash')
            .map(([id]) => id);

        const flashCount = Object.keys(currentFlashes).length;
        const daysSince = currentDay - currentLastFlash;

        if (flashCount < baseData.config.max_flash_events && 
            daysSince >= baseData.config.event_frequency_days && 
            flashCandidates.length > 0) {
            
            const roll = Math.floor(Math.random() * 100) + 1;
            if (roll <= baseData.config.event_chance_percent) {
                const pick = flashCandidates[Math.floor(Math.random() * flashCandidates.length)];
                currentFlashes[pick] = currentDay + baseData.config.flash_duration_days;
                currentLastFlash = currentDay;
            } else {
                currentLastFlash = currentDay - (baseData.config.event_frequency_days - 1);
            }
        }
    }

    setDay(currentDay);
    setLastFlashDay(currentLastFlash);
    setActiveFlash(currentFlashes);
  };

  const resetAll = () => {
    setDay(0);
    setActiveFlash({});
    setLastFlashDay(-10);
    setWallet(1000);
    setInventory({});
    setForcedEvents([]);
    if (selectedTrader && baseData.day0.traderSamples[selectedTrader]) {
        setLocalStock(JSON.parse(JSON.stringify(baseData.day0.traderSamples[selectedTrader].stock)));
    }
  };

  // Helper for prices
  const getPrices = (itemId) => {
    if (!baseData) return { buy: 0, sell: 0 };
    const item = baseData.items[itemId];
    const matrix = baseData.day0.tradeMatrix[itemId]?.[selectedTrader];
    
    let baseBuy = matrix ? matrix.buyPrice : (item?.base_price || 0);
    let baseSell = matrix ? matrix.sellPrice : (item?.base_price || 0) * 0.5;

    const mult = getEventPriceMult(item, activeEventDefs);
    
    return {
        buy: Math.max(1, Math.ceil(baseBuy * mult)),
        sell: Math.max(0, Math.floor(baseSell * mult))
    };
  };

  const buyItem = (itemId) => {
    const prices = getPrices(itemId);
    if (wallet < prices.buy) return;
    if (!localStock[itemId] || localStock[itemId].qty <= 0) return;

    setWallet(w => w - prices.buy);
    setInventory(inv => ({ ...inv, [itemId]: (inv[itemId] || 0) + 1 }));
    setLocalStock(stock => ({
        ...stock,
        [itemId]: { ...stock[itemId], qty: stock[itemId].qty - 1 }
    }));
  };

  const sellItem = (itemId) => {
    const prices = getPrices(itemId);
    if (!inventory[itemId] || inventory[itemId] <= 0) return;

    setWallet(w => w + prices.sell);
    setInventory(inv => {
        const newInv = { ...inv };
        newInv[itemId] -= 1;
        if (newInv[itemId] <= 0) delete newInv[itemId];
        return newInv;
    });
    setLocalStock(stock => {
        const newStock = { ...stock };
        if (!newStock[itemId]) {
            newStock[itemId] = { qty: 0, basePrice: baseData.items[itemId]?.base_price || 0, tags: baseData.items[itemId]?.tags || [] };
        }
        newStock[itemId].qty += 1;
        return newStock;
    });
  };

  const handleTraderChange = (e) => {
    const archId = e.target.value;
    setSelectedTrader(archId);
    if (baseData.day0.traderSamples[archId]) {
        setLocalStock(JSON.parse(JSON.stringify(baseData.day0.traderSamples[archId].stock)));
    }
  };

  if (loading) return <Box display="flex" justifyContent="center" p={10}><CircularProgress /></Box>;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (!baseData) return null;

  const stockChartData = Object.entries(baseData.day0.traderSamples).map(([id, s]) => ({
      name: s.name,
      totalQty: Object.values(s.stock).reduce((a, b) => a + b.qty, 0),
      uniqueItems: Object.keys(s.stock).length
  }));

  return (
    <Box sx={{ width: '100%', pb: 10 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 'bold' }}>Economy Lab</Typography>
        <Box sx={{ display: 'flex', gap: 2 }}>
            <Button variant="outlined" startIcon={<ResetIcon />} onClick={resetAll}>Reset Lab</Button>
            <Button variant="contained" startIcon={<PlayIcon />} onClick={() => advanceDay(1)}>Advance Day</Button>
        </Box>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid item xs={12} md={3}>
            <Card elevation={4} sx={{ background: 'linear-gradient(45deg, #1a237e 30%, #283593 90%)', color: 'white' }}>
                <CardContent>
                    <Typography variant="overline">Current Timeline</Typography>
                    <Typography variant="h3">Day {day}</Typography>
                    <Typography variant="h6">{dayToSeason(day)}</Typography>
                </CardContent>
            </Card>
        </Grid>
        <Grid item xs={12} md={9}>
            <Card elevation={2}>
                <CardContent>
                    <Typography variant="overline">Active Scenarios</Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                        {activeEventDefs.map(ev => (
                            <Chip 
                                key={ev.event_id} 
                                label={ev.name} 
                                color={ev.sentiment === 'good' ? 'success' : ev.sentiment === 'bad' ? 'error' : 'primary'}
                                variant="filled"
                            />
                        ))}
                        {activeEventDefs.length === 0 && <Typography color="text.secondary">No active events.</Typography>}
                    </Box>
                </CardContent>
            </Card>
        </Grid>
      </Grid>

      <Paper elevation={1}>
        <Tabs value={tabValue} onChange={(e, v) => setTabValue(v)} variant="scrollable" scrollButtons="auto">
            <Tab label="Interactive Simulator" />
            <Tab label="Market Analytics" />
            <Tab label="Trade Matrix" />
            <Tab label="Unserved Items" />
        </Tabs>

        {/* --- Tab 0: Interactive Simulator --- */}
        <TabPanel value={tabValue} index={0}>
            <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                    <Box sx={{ mb: 2, display: 'flex', gap: 2, alignItems: 'center' }}>
                        <FormControl sx={{ minWidth: 200 }}>
                            <InputLabel>Selecting Trader</InputLabel>
                            <Select value={selectedTrader} label="Selecting Trader" onChange={handleTraderChange}>
                                {Object.entries(baseData.archetypes).map(([id, arch]) => (
                                    <MenuItem key={id} value={id}>{arch.name}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        <TextField 
                            label="Filter Stock" 
                            size="small" 
                            value={simSearch}
                            onChange={(e) => setSimSearch(e.target.value)}
                            InputProps={{ startAdornment: <InputAdornment position="start"><SearchIcon /></InputAdornment> }}
                        />
                    </Box>
                    
                    <Typography variant="h6" gutterBottom>Trader Stock</Typography>
                    <TableContainer sx={{ maxHeight: 500 }}>
                        <Table stickyHeader size="small">
                            <TableHead>
                                <TableRow>
                                    <TableCell>Item</TableCell>
                                    <TableCell align="center">Stock</TableCell>
                                    <TableCell align="right">Buy Price</TableCell>
                                    <TableCell align="right">Action</TableCell>
                                </TableRow>
                            </TableHead>
                            <TableBody>
                                {Object.entries(localStock)
                                    .filter(([id]) => !simSearch || id.toLowerCase().includes(simSearch.toLowerCase()))
                                    .map(([id, info]) => {
                                        const prices = getPrices(id);
                                        return (
                                            <TableRow key={id} hover>
                                                <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{id}</TableCell>
                                                <TableCell align="center">{info.qty}</TableCell>
                                                <TableCell align="right">${prices.buy}</TableCell>
                                                <TableCell align="right">
                                                    <Button 
                                                        size="small" 
                                                        disabled={info.qty <= 0 || wallet < prices.buy}
                                                        onClick={() => buyItem(id)}
                                                    >Buy</Button>
                                                </TableCell>
                                            </TableRow>
                                        );
                                })}
                            </TableBody>
                        </Table>
                    </TableContainer>
                </Grid>

                <Grid item xs={12} md={4}>
                    <Paper variant="outlined" sx={{ p: 2, bgcolor: 'rgba(255,255,255,0.02)' }}>
                        <Box sx={{ textAlign: 'center', mb: 2 }}>
                            <Typography variant="overline">Your Wallet</Typography>
                            <Typography variant="h4" color="primary.main">${wallet}</Typography>
                        </Box>
                        <Divider sx={{ mb: 2 }} />
                        <Typography variant="subtitle2" gutterBottom>Inventory</Typography>
                        <List dense sx={{ maxHeight: 400, overflow: 'auto' }}>
                            {Object.entries(inventory).map(([id, qty]) => {
                                const prices = getPrices(id);
                                return (
                                    <ListItem key={id} divider>
                                        <ListItemText primary={id} secondary={`Qty: ${qty} | Sell: $${prices.sell}`} />
                                        <ListItemSecondaryAction>
                                            <IconButton size="small" edge="end" onClick={() => sellItem(id)}>
                                                <RemoveIcon />
                                            </IconButton>
                                        </ListItemSecondaryAction>
                                    </ListItem>
                                );
                            })}
                            {Object.keys(inventory).length === 0 && <Typography variant="caption" color="text.secondary">Empty inventory.</Typography>}
                        </List>
                        
                        <Divider sx={{ my: 2 }} />
                        <Typography variant="subtitle2" gutterBottom>Force Event (Scenario)</Typography>
                        <FormControl fullWidth size="small">
                            <Select 
                                displayEmpty
                                value=""
                                onChange={(e) => {
                                    if (e.target.value && !forcedEvents.includes(e.target.value)) {
                                        setForcedEvents([...forcedEvents, e.target.value]);
                                    }
                                }}
                            >
                                <MenuItem disabled value=""><em>Add manual event...</em></MenuItem>
                                {Object.entries(baseData.events).map(([id, ev]) => (
                                    <MenuItem key={id} value={id}>{ev.name}</MenuItem>
                                ))}
                            </Select>
                        </FormControl>
                        {forcedEvents.length > 0 && (
                            <Box sx={{ mt: 1, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                                {forcedEvents.map(id => (
                                    <Chip 
                                        key={id} 
                                        size="small" 
                                        label={id} 
                                        onDelete={() => setForcedEvents(forcedEvents.filter(x => x !== id))}
                                    />
                                ))}
                            </Box>
                        )}
                    </Paper>
                </Grid>
            </Grid>
        </TabPanel>

        {/* --- Tab 1: Market Analytics --- */}
        <TabPanel value={tabValue} index={1}>
            <Typography variant="h6" gutterBottom>Simulated Market Volume by Trader</Typography>
            <Box sx={{ height: 400, width: '100%', mt: 2 }}>
                <ResponsiveContainer>
                    <BarChart data={stockChartData}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                        <XAxis dataKey="name" />
                        <YAxis yAxisId="left" stroke="#8884d8" />
                        <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                        <ChartTooltip contentStyle={{ backgroundColor: '#1e1e1e', border: 'none' }} />
                        <Legend />
                        <Bar yAxisId="left" dataKey="totalQty" name="Total Item Qty" fill="#8884d8" />
                        <Bar yAxisId="right" dataKey="uniqueItems" name="Unique Items" fill="#82ca9d" />
                    </BarChart>
                </ResponsiveContainer>
            </Box>
        </TabPanel>

        {/* --- Tab 2: Trade Matrix --- */}
        <TabPanel value={tabValue} index={2}>
            <TableContainer sx={{ maxHeight: 600 }}>
                <Table stickyHeader size="small">
                    <TableHead>
                        <TableRow>
                            <TableCell>Item ID</TableCell>
                            {Object.values(baseData.archetypes).map(a => <TableCell key={a.archetype_id} align="right">{a.name}</TableCell>)}
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {Object.entries(baseData.day0.tradeMatrix).slice(0, 50).map(([id, row]) => (
                            <TableRow key={id} hover>
                                <TableCell>{id}</TableCell>
                                {Object.keys(baseData.archetypes).map(archId => {
                                    const meta = row[archId];
                                    const { buy, sell } = getPrices(id);
                                    return (
                                        <TableCell key={archId} align="right" sx={{ color: meta.tradeable ? 'success.light' : 'text.disabled' }}>
                                            {meta.tradeable ? `$${buy} / $${sell}` : '-'}
                                        </TableCell>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableBody>
                </Table>
            </TableContainer>
        </TabPanel>

        {/* --- Tab 3: Unserved Items --- */}
        <TabPanel value={tabValue} index={3}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {baseData.day0.unservedItems.map(item => <Chip key={item} label={item} variant="outlined" size="small" />)}
            </Box>
        </TabPanel>
      </Paper>
    </Box>
  );
}
