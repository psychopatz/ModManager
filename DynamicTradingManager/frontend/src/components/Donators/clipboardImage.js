function inferExtension(mimeType) {
  const normalized = String(mimeType || '').toLowerCase();
  if (normalized === 'image/jpeg') return 'jpg';
  if (normalized === 'image/webp') return 'webp';
  if (normalized === 'image/gif') return 'gif';
  if (normalized === 'image/bmp') return 'bmp';
  return 'png';
}

export function getClipboardImageFromPasteEvent(event) {
  const items = Array.from(event?.clipboardData?.items || []);
  const imageItem = items.find((item) => String(item?.type || '').startsWith('image/'));
  return imageItem ? imageItem.getAsFile() : null;
}

export async function readClipboardImageFile() {
  if (!navigator?.clipboard?.read) {
    throw new Error('Clipboard image paste is not supported in this browser.');
  }

  const clipboardItems = await navigator.clipboard.read();
  for (const clipboardItem of clipboardItems) {
    const imageType = clipboardItem.types.find((type) => String(type || '').startsWith('image/'));
    if (!imageType) continue;

    const blob = await clipboardItem.getType(imageType);
    const extension = inferExtension(imageType);
    return new File([blob], `clipboard-donator.${extension}`, { type: imageType });
  }

  throw new Error('Clipboard does not currently contain an image.');
}
