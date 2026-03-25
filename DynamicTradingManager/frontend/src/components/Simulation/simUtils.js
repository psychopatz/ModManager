/**
 * Parity helper functions for DynamicTrading simulation
 */

export const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];

export function dayToSeason(day) {
  const idx = Math.floor(day / 90) % 4;
  return SEASONS[idx];
}

export function tagMatches(itemTags, monitorTag) {
  if (!monitorTag) return true;
  if (!itemTags) return false;
  const tag = monitorTag.toLowerCase();
  return itemTags.some(t => {
    const lowT = t.toLowerCase();
    return lowT === tag || lowT.startsWith(tag + ".") || tag.startsWith(lowT + ".");
  });
}

export function getEventPriceMult(itemDef, activeEvents) {
  let mult = 1.0;
  if (!itemDef || !itemDef.tags) return mult;
  
  for (const ev of activeEvents) {
    if (!ev.effects) continue;
    for (const [tag, effect] of Object.entries(ev.effects)) {
      if (tagMatches(itemDef.tags, tag) && typeof effect.price === 'number') {
        mult *= effect.price;
      }
    }
  }
  return mult;
}

export function getEventVolMult(itemDef, activeEvents) {
  let mult = 1.0;
  if (!itemDef || !itemDef.tags) return mult;
  
  for (const ev of activeEvents) {
    if (!ev.effects) continue;
    for (const [tag, effect] of Object.entries(ev.effects)) {
      if (tagMatches(itemDef.tags, tag) && typeof effect.vol === 'number') {
        mult *= effect.vol;
      }
    }
  }
  return mult;
}
