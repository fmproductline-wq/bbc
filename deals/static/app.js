'use strict';

// ── Category definitions ──────────────────────────────────────────────────────
const CATEGORIES = [
  { name: 'Electronics',      icon: '📱' },
  { name: 'Clothing',         icon: '👗' },
  { name: 'Food & Groceries', icon: '🛒' },
  { name: 'Travel',           icon: '✈️' },
  { name: 'Home & Garden',    icon: '🏡' },
  { name: 'Sports',           icon: '⚽' },
  { name: 'Books & Media',    icon: '📚' },
  { name: 'Beauty',           icon: '💄' },
  { name: 'Gaming',           icon: '🎮' },
  { name: 'Automotive',       icon: '🚗' },
  { name: 'Toys & Kids',      icon: '🧸' },
  { name: 'Health',           icon: '💊' },
];

const PLACEHOLDER_ICONS = {
  'Electronics': '📱', 'Clothing': '👗', 'Food & Groceries': '🛒',
  'Travel': '✈️', 'Home & Garden': '🏡', 'Sports': '⚽',
  'Books & Media': '📚', 'Beauty': '💄', 'Gaming': '🎮',
  'Automotive': '🚗', 'Toys & Kids': '🧸', 'Health': '💊',
};

// ── State ─────────────────────────────────────────────────────────────────────
let selected = new Set();
let allDeals = [];

// ── DOM refs ──────────────────────────────────────────────────────────────────
const catGrid    = document.getElementById('categoryGrid');
const scanBtn    = document.getElementById('scanBtn');
const selCount   = document.getElementById('selCount');
const searchInput= document.getElementById('searchInput');
const clearSearch= document.getElementById('clearSearch');
const statusStrip= document.getElementById('statusStrip');
const botRow     = document.getElementById('botRow');
const statusMsg  = document.getElementById('statusMsg');
const resultsEl  = document.getElementById('results');
const dealGrid   = document.getElementById('dealGrid');
const resultsTitle= document.getElementById('resultsTitle');
const filterInput = document.getElementById('filterInput');
const sortSelect  = document.getElementById('sortSelect');
const noDeals     = document.getElementById('noDeals');

// ── Build category chips ──────────────────────────────────────────────────────
function buildCategories() {
  catGrid.innerHTML = '';
  CATEGORIES.forEach(({ name, icon }) => {
    const chip = document.createElement('div');
    chip.className = 'cat-chip';
    chip.dataset.cat = name;
    chip.innerHTML = `<span class="cat-icon">${icon}</span><span>${name}</span><span class="check"></span>`;
    chip.addEventListener('click', () => toggleCat(name, chip));
    catGrid.appendChild(chip);
  });
}

function toggleCat(name, chip) {
  if (selected.has(name)) {
    selected.delete(name);
    chip.classList.remove('selected');
  } else {
    selected.add(name);
    chip.classList.add('selected');
  }
  updateScanBtn();
}

function updateScanBtn() {
  const n = selected.size;
  selCount.textContent = `${n} categor${n === 1 ? 'y' : 'ies'} selected`;
  scanBtn.disabled = n === 0;
}

document.getElementById('selectAll').addEventListener('click', () => {
  CATEGORIES.forEach(({ name }) => selected.add(name));
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.add('selected'));
  updateScanBtn();
});

document.getElementById('clearAll').addEventListener('click', () => {
  selected.clear();
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('selected'));
  updateScanBtn();
});

clearSearch.addEventListener('click', () => { searchInput.value = ''; searchInput.focus(); });

// ── Bot status animation ──────────────────────────────────────────────────────
function showBotStatus(categories) {
  botRow.innerHTML = '';
  categories.forEach(cat => {
    const icon = PLACEHOLDER_ICONS[cat] || '🤖';
    const pill = document.createElement('div');
    pill.className = 'bot-pill scanning';
    pill.id = `bot-${cat.replace(/\s+/g, '-')}`;
    pill.innerHTML = `<span class="dot"></span><span>${icon} ${cat}</span>`;
    botRow.appendChild(pill);
  });
  statusStrip.classList.remove('hidden');
  statusMsg.textContent = 'Bots are scanning the web for deals…';
}

function markBotDone(cat) {
  const pill = document.getElementById(`bot-${cat.replace(/\s+/g, '-')}`);
  if (pill) { pill.className = 'bot-pill done'; }
}

function hideBotStatus() {
  statusMsg.textContent = 'Scan complete!';
  setTimeout(() => statusStrip.classList.add('hidden'), 2000);
}

// ── Scan ──────────────────────────────────────────────────────────────────────
scanBtn.addEventListener('click', async () => {
  const categories = [...selected];
  const query = searchInput.value.trim();

  // animate bots
  showBotStatus(categories);
  scanBtn.classList.add('loading');
  scanBtn.disabled = true;
  resultsEl.classList.add('hidden');

  // fake per-bot "completion" animation while waiting
  let idx = 0;
  const animInterval = setInterval(() => {
    if (idx < categories.length) markBotDone(categories[idx++]);
  }, 1200);

  try {
    const res = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ categories, query }),
    });
    clearInterval(animInterval);
    categories.forEach(c => markBotDone(c));

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Scan failed');
    }

    const data = await res.json();
    allDeals = data.deals || [];
    renderDeals(allDeals);
    hideBotStatus();
  } catch (e) {
    clearInterval(animInterval);
    statusMsg.textContent = `Error: ${e.message}`;
    setTimeout(() => statusStrip.classList.add('hidden'), 4000);
  } finally {
    scanBtn.classList.remove('loading');
    scanBtn.disabled = selected.size === 0;
  }
});

// ── Render deals ──────────────────────────────────────────────────────────────
function renderDeals(deals) {
  dealGrid.innerHTML = '';
  resultsTitle.textContent = `${deals.length} Deal${deals.length !== 1 ? 's' : ''} Found`;

  if (deals.length === 0) {
    noDeals.classList.remove('hidden');
    resultsEl.classList.remove('hidden');
    return;
  }
  noDeals.classList.add('hidden');

  deals.forEach(deal => dealGrid.appendChild(buildCard(deal)));
  resultsEl.classList.remove('hidden');
  resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildCard(deal) {
  const card = document.createElement('div');
  card.className = 'deal-card';
  card.dataset.json = JSON.stringify(deal);

  const icon = PLACEHOLDER_ICONS[deal.category] || '🏷️';

  // image section
  let imgHtml;
  if (deal.image_url) {
    imgHtml = `<img class="card-img" src="${esc(deal.image_url)}" alt="${esc(deal.title)}"
      onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
      <div class="card-img-placeholder" style="display:none">${icon}</div>`;
  } else {
    imgHtml = `<div class="card-img-placeholder">${icon}</div>`;
  }

  // price block
  const priceNow = deal.price ? `<span class="price-now">${esc(deal.price)}</span>` : '';
  const priceWas = deal.original_price ? `<span class="price-was">${esc(deal.original_price)}</span>` : '';
  const disc     = deal.discount ? `<span class="badge-discount">${esc(deal.discount)} OFF</span>` : '';

  // meta chips
  const chips = [];
  if (deal.store)       chips.push(`<span class="meta-chip"><span class="icon">🏪</span>${esc(deal.store)}</span>`);
  if (deal.shipping)    chips.push(`<span class="meta-chip shipping"><span class="icon">📦</span>${esc(deal.shipping)}</span>`);
  if (deal.location && deal.location !== 'Online')
                         chips.push(`<span class="meta-chip"><span class="icon">📍</span>${esc(deal.location)}</span>`);
  if (deal.coupon_code) chips.push(`<span class="meta-chip coupon"><span class="icon">🎟️</span>${esc(deal.coupon_code)}</span>`);
  if (deal.expiry)      chips.push(`<span class="meta-chip expiry"><span class="icon">⏰</span>${esc(deal.expiry)}</span>`);

  const dealHref = deal.deal_url || '#';
  const isExternal = deal.deal_url && deal.deal_url.startsWith('http');

  card.innerHTML = `
    ${imgHtml}
    <div class="card-body">
      <span class="card-cat">${icon} ${esc(deal.category || '')}</span>
      <div class="card-title">${esc(deal.title || 'Deal')}</div>
      ${deal.summary ? `<div class="card-summary">${esc(deal.summary)}</div>` : ''}
      <div class="card-price-row">${priceNow}${priceWas}${disc}</div>
      <div class="card-meta">${chips.join('')}</div>
    </div>
    <div class="card-footer">
      <a class="btn-deal" href="${esc(dealHref)}" ${isExternal ? 'target="_blank" rel="noopener"' : ''}>
        View Deal →
      </a>
      <button class="btn-share" title="Copy link" onclick="copyLink(this, '${esc(dealHref)}')">🔗</button>
    </div>
  `;
  return card;
}

function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

window.copyLink = function(btn, url) {
  navigator.clipboard.writeText(url).then(() => {
    btn.textContent = '✅';
    setTimeout(() => { btn.textContent = '🔗'; }, 1500);
  });
};

// ── Filter & Sort ─────────────────────────────────────────────────────────────
function parsePrice(str) {
  if (!str) return Infinity;
  const n = parseFloat(String(str).replace(/[^0-9.]/g, ''));
  return isNaN(n) ? Infinity : n;
}
function parseDiscount(str) {
  if (!str) return 0;
  const n = parseFloat(String(str).replace(/[^0-9.]/g, ''));
  return isNaN(n) ? 0 : n;
}

function applyFilterSort() {
  const q = filterInput.value.toLowerCase();
  const sort = sortSelect.value;

  let deals = allDeals.filter(d => {
    if (!q) return true;
    return [d.title, d.store, d.category, d.summary, d.coupon_code]
      .some(f => f && String(f).toLowerCase().includes(q));
  });

  if (sort === 'price_asc')  deals.sort((a,b) => parsePrice(a.price) - parsePrice(b.price));
  if (sort === 'price_desc') deals.sort((a,b) => parsePrice(b.price) - parsePrice(a.price));
  if (sort === 'discount')   deals.sort((a,b) => parseDiscount(b.discount) - parseDiscount(a.discount));

  dealGrid.innerHTML = '';
  noDeals.classList.toggle('hidden', deals.length > 0);
  resultsTitle.textContent = `${deals.length} Deal${deals.length !== 1 ? 's' : ''} Found`;
  deals.forEach(d => dealGrid.appendChild(buildCard(d)));
}

filterInput.addEventListener('input', applyFilterSort);
sortSelect.addEventListener('change', applyFilterSort);

// ── Init ──────────────────────────────────────────────────────────────────────
buildCategories();
updateScanBtn();
