export const formatPrice = (value) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) {
    return String(value ?? '');
  }
  return `${num > 0 ? '+' : ''}${num}`;
};

export const formatPreviewNumber = (value) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) {
    return String(value ?? '');
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits: Math.abs(num) >= 1000 ? 0 : 2,
  }).format(num);
};

export const formatCompactDelta = (value) => {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) {
    return String(value ?? '');
  }
  return `${num > 0 ? '+' : ''}${new Intl.NumberFormat('en-US', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Math.abs(num))}`;
};
