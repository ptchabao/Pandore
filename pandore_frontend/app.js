const state = {
  overview: null,
  creatorMap: {}
};

const els = {
  heroTitle: document.querySelector('#heroTitle'),
  heroSubtitle: document.querySelector('#heroSubtitle'),
  continueSection: document.querySelector('#continueSection'),
  recentSection: document.querySelector('#recentSection'),
  creatorsSection: document.querySelector('#creatorsSection'),
  dateSection: document.querySelector('#dateSection'),
  searchResults: document.querySelector('#searchResults'),
  liveView: document.querySelector('#liveView'),
  creatorView: document.querySelector('#creatorView'),
  creatorTitle: document.querySelector('#creatorTitle'),
  creatorStats: document.querySelector('#creatorStats'),
  creatorGrid: document.querySelector('#creatorGrid'),
  player: document.querySelector('#player'),
  playerCreator: document.querySelector('#playerCreator'),
  playerTime: document.querySelector('#playerTime'),
  liveTitle: document.querySelector('#liveTitle'),
  liveCreator: document.querySelector('#liveCreator'),
  liveDate: document.querySelector('#liveDate'),
  liveDuration: document.querySelector('#liveDuration'),
  relatedSection: document.querySelector('#relatedSection'),
  searchInput: document.querySelector('#searchInput')
};

function formatDate(dateString) {
  return new Date(dateString).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' });
}

function formatCompactDuration(seconds) {
  if (!seconds) return '0m';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function cardMarkup(item, compact = false) {
  const creator = item.creator || item.name || 'Créateur';
  const title = item.title || creator;
  const badge = item.isNew ? '<span class="new-badge">Nouveau</span>' : '';
  const progress = item.progress ? `<div class="progress-bar"><span style="width:${Math.round(item.progress * 100)}%"></span></div>` : '';
  const summary = compact ? creator.slice(0, 2).toUpperCase() : creator.slice(0, 2).toUpperCase();
  const liveMeta = item.id ? `<p>${formatDate(item.date)}</p><p>${item.durationLabel}</p>` : `<p>${item.count || 0} lives</p><p>${formatCompactDuration(item.totalDuration)}</p>`;
  const dataAttrs = item.id ? `data-live-id="${item.id}"` : `data-creator-slug="${item.creatorSlug}"`;
  return `
    <article class="card" ${dataAttrs}>
      <div class="card-media">
        <span class="card-symbol">${summary}</span>
        <span>${badge || '<span class="new-badge">Archive</span>'}</span>
      </div>
      <div class="card-body">
        <h3>${title}</h3>
        <p>${creator}</p>
        ${liveMeta}
        ${progress}
      </div>
    </article>
  `;
}

function renderRow(title, items, target, options = {}) {
  const list = items.map((item) => cardMarkup(item, options.compact)).join('');
  target.innerHTML = `
    <h2 class="row-title">${title}</h2>
    <div class="card-row">${list}</div>
  `;
}

function renderOverview(data) {
  state.overview = data;
  els.heroTitle.textContent = data.hero.title;
  els.heroSubtitle.textContent = data.hero.subtitle;
  renderRow('Continue à regarder', data.continueWatching, els.continueSection);
  renderRow('Lives récents', data.recent.slice(0, 6), els.recentSection, { compact: true });
  renderRow('Par créateur', data.creators, els.creatorsSection, { compact: true });
  const dateHtml = data.dateGroups.map(group => `
    <div class="date-group">
      <h3>${group.label}</h3>
      <div class="card-row">${group.items.map(item => cardMarkup(item, true)).join('')}</div>
    </div>
  `).join('');
  els.dateSection.innerHTML = `<h2 class="row-title">Par date</h2>${dateHtml}`;
}

function renderLive(live) {
  const { live: entry, suggestions } = live;
  els.liveView.classList.remove('hidden');
  els.creatorView.classList.add('hidden');
  els.searchResults.classList.add('hidden');
  els.player.poster = entry.thumbnail || '/assets/pandore-temple.svg';
  els.player.src = entry.videoUrl;
  els.player.load();
  els.playerCreator.textContent = entry.creator;
  els.playerTime.textContent = formatDate(entry.date);
  els.liveTitle.textContent = entry.title;
  els.liveCreator.textContent = `Créateur : ${entry.creator}`;
  els.liveDate.textContent = `Date : ${formatDate(entry.date)}`;
  els.liveDuration.textContent = `Durée : ${entry.durationLabel}`;
  els.relatedSection.innerHTML = `<h3>Autres lives de ce créateur</h3>${suggestions.map(item => `<div class="mini-link" data-live-id="${item.id}">${item.title}</div>`).join('')}`;
}

function renderCreatorPage(data) {
  els.liveView.classList.add('hidden');
  els.creatorView.classList.remove('hidden');
  els.searchResults.classList.add('hidden');
  els.creatorTitle.textContent = data.creator;
  els.creatorStats.innerHTML = `
    <span class="stat-chip">${data.stats.count} lives</span>
    <span class="stat-chip">${formatCompactDuration(data.stats.totalDuration)}</span>
    <span class="stat-chip">Dernier live : ${formatDate(data.stats.lastLive)}</span>
  `;
  els.creatorGrid.innerHTML = data.items.map((item) => cardMarkup(item, true)).join('');
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  return response.json();
}

async function loadOverview() {
  const data = await fetchJson('/api/overview');
  renderOverview(data);
}

async function search(query) {
  if (!query.trim()) {
    els.searchResults.classList.add('hidden');
    return;
  }
  const data = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  if (!data.items.length) {
    els.searchResults.innerHTML = '<h2 class="row-title">Aucun résultat</h2>';
    els.searchResults.classList.remove('hidden');
    return;
  }
  renderRow('Résultats de recherche', data.items.slice(0, 12), els.searchResults, { compact: true });
  els.searchResults.classList.remove('hidden');
}

async function openLiveById(liveId) {
  const payload = await fetchJson(`/api/live/${liveId}`);
  renderLive(payload);
}

async function openCreator(slug) {
  const payload = await fetchJson(`/api/creator/${slug}`);
  renderCreatorPage(payload);
}

function attachEvents() {
  document.addEventListener('click', async (event) => {
    const creatorCard = event.target.closest('[data-creator-slug]');
    if (creatorCard && !creatorCard.dataset.liveId) {
      await openCreator(creatorCard.dataset.creatorSlug);
      return;
    }

    const card = event.target.closest('[data-live-id]');
    if (!card) return;
    const liveId = card.dataset.liveId;
    await openLiveById(liveId);
  });

  els.searchInput.addEventListener('input', (event) => {
    window.clearTimeout(window.searchDebounce);
    window.searchDebounce = window.setTimeout(() => search(event.target.value), 250);
  });
}

attachEvents();
loadOverview();
