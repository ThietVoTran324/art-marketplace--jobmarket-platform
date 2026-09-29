/** Case + Vietnamese diacritic fold for client-side search filters. */
export function foldSearchText(value) {
  if (!value) return '';
  return String(value)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}
