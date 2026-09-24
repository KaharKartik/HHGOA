export function fmtMoney(n) {
  if (n === null || n === undefined) return '$0.00';
  return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtProb(p) {
  if (p === null || p === undefined) return '0.0%';
  return (Number(p) * 100).toFixed(1) + '%';
}

export function getVerdictClass(v) {
  if (!v) return 'badge-pending';
  const lv = String(v).toLowerCase();
  if (lv === 'fraud') return 'badge-fraud';
  if (lv === 'legitimate') return 'badge-legit';
  return 'badge-uncertain';
}

export function getRouteClass(r) {
  if (!r) return 'route-auto';
  const lr = String(r).toLowerCase();
  if (lr === 'l2') return 'route-l2';
  if (lr === 'l1') return 'route-l1';
  return 'route-auto';
}
