const fmt = (n) => n != null ? '₪' + n.toLocaleString('en-IL', { minimumFractionDigits: 2 }) : '—';

function statusClass(s) {
  const l = s.toLowerCase();
  if (l.includes('ship')) return 'status-shipped';
  if (l.includes('complet')) return 'status-completed';
  return 'status-invoice';
}

function catClass(c) {
  const l = c.toLowerCase();
  if (l.includes('tobacco')) return 'cat-tobacco';
  if (l.includes('cloth') || l.includes('shop')) return 'cat-clothing';
  if (l.includes('din')) return 'cat-dining';
  if (l.includes('well')) return 'cat-wellness';
  return 'cat-services';
}

async function load() {
  const res = await fetch('data.json?t=' + Date.now());
  const d = await res.json();

  // Subtitle
  document.getElementById('subtitle').textContent = d.week + '  ·  Generated ' + d.generated;

  // Stat cards
  document.getElementById('stats').innerHTML = `
    <div class="stat-card">
      <div class="label">Total Spent</div>
      <div class="value" style="color:var(--red)">${fmt(d.summary.totalSpent)}</div>
      <div class="sub">Across ${d.summary.transactionCount} transactions</div>
    </div>
    <div class="stat-card">
      <div class="label">Largest Purchase</div>
      <div class="value" style="color:var(--orange)">${fmt(d.summary.largestPurchase.amount)}</div>
      <div class="sub">${d.summary.largestPurchase.merchant}</div>
    </div>
    <div class="stat-card">
      <div class="label">Cibus (Employer)</div>
      <div class="value" style="color:var(--green)">${fmt(d.summary.cibus.amount)}</div>
      <div class="sub">${d.summary.cibus.note}</div>
    </div>
    <div class="stat-card">
      <div class="label">Categories</div>
      <div class="value" style="color:var(--accent)">${d.summary.categories.length}</div>
      <div class="sub">${d.summary.categories.join(', ')}</div>
    </div>`;

  // Category chart
  document.getElementById('chart-bar').innerHTML = d.categoryBreakdown.map(c =>
    `<div style="width:${c.percent}%;background:${c.color}" title="${c.name}: ${fmt(c.amount)}">${fmt(c.amount)}</div>`
  ).join('');

  document.getElementById('legend').innerHTML = d.categoryBreakdown.map(c =>
    `<div class="legend-item"><div class="legend-dot" style="background:${c.color}"></div> ${c.name} (${c.percent}%)</div>`
  ).join('');

  // Transactions
  document.getElementById('txn-body').innerHTML = d.transactions.map(t => `
    <tr>
      <td>${t.date}</td>
      <td><strong>${t.merchant}</strong>${t.details ? '<br><span class="muted small">' + t.details + '</span>' : ''}</td>
      <td><span class="cat-badge ${catClass(t.category)}">${t.category}</span></td>
      <td>${t.payment}</td>
      <td class="amount"${t.amount == null ? ' style="color:var(--muted)"' : ''}>${fmt(t.amount)}</td>
      <td><span class="status-badge ${statusClass(t.status)}">${t.status}</span></td>
    </tr>`).join('');

  // Cibus
  const cibusTotal = d.cibusCharges.reduce((s, c) => s + c.chargedToCard, 0);
  document.getElementById('cibus-body').innerHTML =
    d.cibusCharges.map(c => `
      <tr>
        <td>${c.date}</td>
        <td>${c.merchant}</td>
        <td>${fmt(c.transactionPrice)}</td>
        <td class="amount">${fmt(c.chargedToCard)}</td>
      </tr>`).join('') +
    `<tr>
      <td colspan="3" style="text-align:right;font-weight:600;">Total charged to card ending ${d.cibusCardEnding}</td>
      <td class="amount" style="font-weight:700;">${fmt(cibusTotal)}</td>
    </tr>`;
  document.getElementById('cibus-note').textContent =
    'Previous-month charges billed to credit card. Employer subsidizes part of the meal cost via Cibus.';

  // Orders
  document.getElementById('orders-body').innerHTML = d.orders.map(o => `
    <tr>
      <td><strong>${o.orderId}</strong></td>
      <td>${o.store}</td>
      <td>${o.items}</td>
      <td><span class="status-badge status-shipped">${o.status}</span></td>
      <td>${o.tracking}</td>
    </tr>`).join('');

  // Alerts
  document.getElementById('alerts').innerHTML = d.alerts.map(a => `
    <div class="flag ${a.type}">
      <div class="flag-icon">${a.icon}</div>
      <div class="flag-text">
        <strong>${a.title}</strong>
        ${a.text}
      </div>
    </div>`).join('');

  // Subscriptions
  document.getElementById('subs-note').textContent = d.subscriptions.note;
}

load().catch(err => {
  document.getElementById('subtitle').textContent = 'Error loading data: ' + err.message;
});
