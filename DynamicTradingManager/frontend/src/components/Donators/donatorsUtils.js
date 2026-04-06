let supporterUiKeyCounter = 0;

export const createSupporterUiKey = (seed = 'supporter') => {
  supporterUiKeyCounter += 1;
  return `${seed}_${supporterUiKeyCounter}`;
};

export const slugifyDonator = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[^a-z0-9_-]+/g, '_')
  .replace(/_+/g, '_')
  .replace(/^_+|_+$/g, '');

export const createEmptySupporter = (index = 1) => ({
  ui_key: createSupporterUiKey(`supporter_${index}`),
  id: `supporter_${index}`,
  name: '',
  total_donation: 0,
  image_path: '',
  active: true,
});

export const sortSupporters = (entries) => [...(entries || [])].sort((left, right) => {
  const totalDelta = Number(right?.total_donation || 0) - Number(left?.total_donation || 0);
  if (totalDelta !== 0) return totalDelta;
  return String(left?.name || '').localeCompare(String(right?.name || ''), undefined, { sensitivity: 'base' });
});

export const formatDonation = (value, currencySymbol = '$') => {
  const amount = Number(value || 0);
  const safeAmount = Number.isFinite(amount) ? amount : 0;
  const decimals = Math.abs(safeAmount % 1) > 0.0001 ? 2 : 0;
  return `${currencySymbol}${safeAmount.toFixed(decimals)}`;
};

export const resolveDonatorImageUrl = (backendOrigin, assetBaseUrl, imagePath) => {
  if (!imagePath) return '';
  const normalized = String(imagePath);
  if (normalized.startsWith('media/ui/Manuals/')) {
    const suffix = normalized.replace('media/ui/Manuals/', '').split('/').slice(1).join('/');
    return `${backendOrigin}${assetBaseUrl}/${suffix}`;
  }
  return normalized;
};
