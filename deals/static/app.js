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

const ICON_MAP = Object.fromEntries(CATEGORIES.map(c => [c.name, c.icon]));

// ── State ─────────────────────────────────────────────────────────────────────
let selected = new Set();
let allDeals  = [];
let scanning  = false;

// ── DOM refs ──────────────────────────────────────────────────────────────────
const catGrid     = document.getElementById('categoryGrid');
const scanBtn     = document.getElementById('scanBtn');
const scanBtnText = document.getElementById('scanBtnText');
const selCount    = document.getElementById('selCount');
const searchInput = document.getElementById('searchInput');
const clearSearch = document.getElementById('clearSearch');
const statusStrip = document.getElementById('statusStrip');
const botRow      = document.getElementById('botRow');
const statusMsg   = document.getElementById('statusMsg');
const resultsEl   = document.getElementById('results');
const dealGrid    = document.getElementById('dealGrid');
const resultsTitle= document.getElementById('resultsTitle');
const filterInput = document.getElementById('filterInput');
const sortSelect  = document.getElementById('sortSelect');
const noDeals     = document.getElementById('noDeals');

// ── Helpers ───────────────────────────────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g,  '&amp;')
    .replace(/</g,  '&lt;')
    .replace(/>/g,  '&gt;')
    .replace(/"/g,  '&quot;')
    .replace(/'/g,  '&#39;');
}

/** Safe ID token — strips everything except letters, digits and hyphens. */
function safeId(str) {
  return 'bot-' + String(str).replace(/[^a-zA-Z0-9]/g, '-');
}

// ── Category chips ────────────────────────────────────────────────────────────
function buildCategories() {
  catGrid.innerHTML = '';
  CATEGORIES.forEach(({ name, icon }) => {
    const chip = document.createElement('div');
    chip.className   = 'cat-chip';
    chip.dataset.cat = name;
    chip.innerHTML   = `<span class="cat-icon">${icon}</span><span>${name}</span><span class="check"></span>`;
    chip.addEventListener('click', () => {
      if (scanning) return;          // lock chips during scan
      if (selected.has(name)) {
        selected.delete(name);
        chip.classList.remove('selected');
      } else {
        selected.add(name);
        chip.classList.add('selected');
      }
      updateScanBtn();
    });
    catGrid.appendChild(chip);
  });
}

function updateScanBtn() {
  const n = selected.size;
  selCount.textContent = `${n} categor${n === 1 ? 'y' : 'ies'} selected`;
  scanBtn.disabled = n === 0 || scanning;
}

document.getElementById('selectAll').addEventListener('click', () => {
  if (scanning) return;
  CATEGORIES.forEach(({ name }) => selected.add(name));
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.add('selected'));
  updateScanBtn();
});

document.getElementById('clearAll').addEventListener('click', () => {
  if (scanning) return;
  selected.clear();
  document.querySelectorAll('.cat-chip').forEach(c => c.classList.remove('selected'));
  updateScanBtn();
});

clearSearch.addEventListener('click', () => {
  searchInput.value = '';
  searchInput.focus();
});

// Pressing Enter in the search box triggers the scan
searchInput.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !scanBtn.disabled) startScan();
});

// ── Bot status UI ─────────────────────────────────────────────────────────────
function showBotStatus(categories) {
  botRow.innerHTML = '';
  categories.forEach(cat => {
    const icon = ICON_MAP[cat] || '🤖';
    const pill = document.createElement('div');
    pill.className = 'bot-pill scanning';
    pill.id        = safeId(cat);           // no & or spaces in id
    pill.innerHTML = `<span class="dot"></span><span>${icon} ${cat}</span>`;
    botRow.appendChild(pill);
  });
  statusStrip.classList.remove('hidden');
  statusMsg.textContent = 'Bots are scanning the web for deals…';
}

function markBotDone(cat) {
  const pill = document.getElementById(safeId(cat));
  if (pill) pill.className = 'bot-pill done';
}

function hideBotStatus(success) {
  statusMsg.textContent = success ? 'Scan complete!' : 'Scan failed — check your API key and try again.';
  setTimeout(() => statusStrip.classList.add('hidden'), 2500);
}

// ── Scan flow ─────────────────────────────────────────────────────────────────
function startScan() {
  if (scanning || selected.size === 0) return;

  const categories = [...selected];
  const query      = searchInput.value.trim();

  scanning = true;
  scanBtn.classList.add('loading');
  scanBtn.disabled       = true;
  scanBtnText.textContent = 'Scanning…';

  // Reset filter/sort so new results aren't hidden by a stale filter
  filterInput.value  = '';
  sortSelect.value   = 'default';
  resultsEl.classList.add('hidden');

  showBotStatus(categories);

  // Staggered visual animation: mark bots done over time while real scan runs
  let idx = 0;
  const animInterval = setInterval(() => {
    if (idx < categories.length) markBotDone(categories[idx++]);
  }, Math.max(800, Math.floor(1800 / categories.length)));

  fetch('/api/scan', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ categories, query }),
  })
    .then(async res => {
      clearInterval(animInterval);
      categories.forEach(c => markBotDone(c));   // mark all done on response

      if (!res.ok) {
        let msg = 'Scan failed';
        try { msg = (await res.json()).detail || msg; } catch (_) {}
        throw new Error(msg);
      }
      return res.json();
    })
    .then(data => {
      allDeals = data.deals || [];
      renderDeals(allDeals);
      hideBotStatus(true);
    })
    .catch(err => {
      clearInterval(animInterval);
      hideBotStatus(false);
      console.error('Scan error:', err);
    })
    .finally(() => {
      scanning = false;
      scanBtn.classList.remove('loading');
      scanBtnText.textContent = 'Scan for Deals';
      updateScanBtn();
    });
}

scanBtn.addEventListener('click', startScan);

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
  // Slight delay so the section is visible before scrolling
  setTimeout(() => resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' }), 60);
}

function buildCard(deal) {
  const card = document.createElement('div');
  card.className = 'deal-card';

  const icon       = ICON_MAP[deal.category] || '🏷️';
  const dealHref   = (deal.deal_url && deal.deal_url.startsWith('http')) ? deal.deal_url : '#';
  const isExternal = dealHref !== '#';

  // Image section — placeholder shown when URL is absent or broken
  const imgSection = deal.image_url
    ? `<img class="card-img" src="${esc(deal.image_url)}" alt="${esc(deal.title)}"
         onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/>
       <div class="card-img-placeholder" style="display:none">${icon}</div>`
    : `<div class="card-img-placeholder">${icon}</div>`;

  // Price block
  const priceNow = deal.price          ? `<span class="price-now">${esc(deal.price)}</span>` : '';
  const priceWas = deal.original_price ? `<span class="price-was">${esc(deal.original_price)}</span>` : '';
  const disc     = deal.discount       ? `<span class="badge-discount">${esc(deal.discount)} OFF</span>` : '';

  // Meta chips
  const chips = [];
  if (deal.store)       chips.push(`<span class="meta-chip"><span class="icon">🏪</span>${esc(deal.store)}</span>`);
  if (deal.shipping)    chips.push(`<span class="meta-chip shipping"><span class="icon">📦</span>${esc(deal.shipping)}</span>`);
  if (deal.location && deal.location !== 'Online')
                        chips.push(`<span class="meta-chip"><span class="icon">📍</span>${esc(deal.location)}</span>`);
  if (deal.coupon_code) chips.push(`<span class="meta-chip coupon"><span class="icon">🎟️</span>${esc(deal.coupon_code)}</span>`);
  if (deal.expiry)      chips.push(`<span class="meta-chip expiry"><span class="icon">⏰</span>${esc(deal.expiry)}</span>`);

  card.innerHTML = `
    ${imgSection}
    <div class="card-body">
      <span class="card-cat">${icon} ${esc(deal.category || '')}</span>
      <div class="card-title">${esc(deal.title || 'Deal')}</div>
      ${deal.summary ? `<div class="card-summary">${esc(deal.summary)}</div>` : ''}
      <div class="card-price-row">${priceNow}${priceWas}${disc}</div>
      <div class="card-meta">${chips.join('')}</div>
    </div>
    <div class="card-footer">
      <a class="btn-deal" href="${esc(dealHref)}"
         ${isExternal ? 'target="_blank" rel="noopener noreferrer"' : 'aria-disabled="true"'}>
        ${isExternal ? 'View Deal →' : 'No link available'}
      </a>
      <button class="btn-share" title="Copy link" data-url="${esc(dealHref)}">🔗</button>
    </div>
  `;

  // Wire copy-link via event listener, not inline onclick — avoids quoting issues
  card.querySelector('.btn-share').addEventListener('click', function () {
    const url = this.dataset.url;
    if (!url || url === '#') return;
    navigator.clipboard.writeText(url)
      .then(() => {
        this.textContent = '✅';
        setTimeout(() => { this.textContent = '🔗'; }, 1500);
      })
      .catch(() => {
        // Fallback for non-HTTPS contexts
        const ta = document.createElement('textarea');
        ta.value = url;
        ta.style.position = 'fixed';
        ta.style.opacity  = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        this.textContent = '✅';
        setTimeout(() => { this.textContent = '🔗'; }, 1500);
      });
  });

  return card;
}

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
  // No-op until at least one scan has completed
  if (allDeals.length === 0 && resultsEl.classList.contains('hidden')) return;

  const q    = filterInput.value.toLowerCase().trim();
  const sort = sortSelect.value;

  let deals = allDeals.filter(d => {
    if (!q) return true;
    return [d.title, d.store, d.category, d.summary, d.coupon_code]
      .some(f => f && String(f).toLowerCase().includes(q));
  });

  if (sort === 'price_asc')  deals.sort((a, b) => parsePrice(a.price)      - parsePrice(b.price));
  if (sort === 'price_desc') deals.sort((a, b) => parsePrice(b.price)      - parsePrice(a.price));
  if (sort === 'discount')   deals.sort((a, b) => parseDiscount(b.discount) - parseDiscount(a.discount));

  dealGrid.innerHTML = '';
  noDeals.classList.toggle('hidden', deals.length > 0);
  resultsTitle.textContent = `${deals.length} Deal${deals.length !== 1 ? 's' : ''} Found`;
  deals.forEach(d => dealGrid.appendChild(buildCard(d)));
}

filterInput.addEventListener('input',  applyFilterSort);
sortSelect.addEventListener('change', applyFilterSort);

// ── Init ──────────────────────────────────────────────────────────────────────
buildCategories();
updateScanBtn();
