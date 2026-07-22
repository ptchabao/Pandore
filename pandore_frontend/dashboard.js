const $ = (selector) => document.querySelector(selector);
const state = { overview: null };

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.detail || payload.error || 'Une erreur est survenue');
  return payload;
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
}

function formatDate(value) {
  if (!value) return 'Date inconnue';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

function videoCard(item, continued = false) {
  const creator = escapeHtml(item.creator || item.name || 'Créateur');
  const title = escapeHtml(item.title || creator);
  const thumbnail = item.thumbnail ? `<img src="${item.thumbnail}" alt="${creator}" loading="lazy" />` : `<span class="thumbnail-placeholder">${creator.slice(0, 2).toUpperCase()}</span>`;
  const progress = continued ? `<div class="video-progress"><span style="width:${Math.round((item.progress || .35) * 100)}%"></span></div>` : '';
  return `<article class="video-card" data-live-id="${escapeHtml(item.id || '')}">
    <div class="video-thumbnail">${thumbnail}<span class="play-overlay">▶</span><span class="video-duration">${escapeHtml(item.durationLabel || 'Archive')}</span><button class="card-more" aria-label="Actions">•••</button></div>
    <div class="video-info"><div class="video-creator"><span class="tiny-avatar">${creator.slice(0, 2).toUpperCase()}</span><span>${creator}</span></div><h3>${title}</h3><p>${escapeHtml(item.platform || 'TikTok')} · ${formatDate(item.date)}</p>${progress}</div>
  </article>`;
}

function emptyState(message) { return `<div class="empty-state">${escapeHtml(message)}</div>`; }

function renderOverview(data) {
  state.overview = data;
  const recent = data.recent || [];
  const recordings = data.storage?.recordingsCount || recent.length;
  const hours = Math.round((data.storage?.totalBytes || 0) / (1024 * 1024 * 1024));
  $('#metricLives').textContent = recordings.toLocaleString('fr-FR');
  $('#metricHours').textContent = `${hours || '—'}${hours ? ' h' : ''}`;
  $('#metricCreators').textContent = (data.creators || data.accounts || []).length;
  $('#continueGrid').innerHTML = (data.continueWatching || recent.slice(0, 4)).slice(0, 4).map((item) => videoCard(item, true)).join('') || emptyState('Aucun live à reprendre');
  $('#recordingsGrid').innerHTML = recent.slice(0, 8).map((item) => videoCard(item)).join('') || emptyState('Aucun enregistrement disponible');
  renderAccounts(data.accounts || []);
}

function renderAccounts(accounts) {
  $('#metricCreators').textContent = accounts.length || state.overview?.creators?.length || 0;
  $('#dashboardAccounts').innerHTML = accounts.slice(0, 8).map((account) => {
    const name = escapeHtml(account.name || account.creatorSlug || 'Créateur');
    const slug = escapeHtml(account.creatorSlug || account.username || '');
    return `<article class="creator-card"><div class="creator-avatar">${name.slice(0, 2).toUpperCase()}<span class="online-dot"></span></div><div class="creator-details"><strong>${name}</strong><small>@${slug}</small><span>● Actif · ${account.totalLives || '—'} lives</span></div><button class="creator-remove" data-delete-account="${slug}" title="Retirer">×</button></article>`;
  }).join('') || emptyState('Aucun compte suivi pour le moment');
}

async function loadOverview() {
  try { renderOverview(await fetchJson('/api/overview')); } catch (error) {
    if (error.message === 'Authentication required' || error.message.includes('session')) { window.location.href = '/login'; return; }
    console.error(error); $('#recordingsGrid').innerHTML = emptyState('Impossible de charger la bibliothèque');
  }
}

async function loadAccounts() { renderAccounts((await fetchJson('/api/overview')).accounts || []); }

async function addAccount(event) {
  event.preventDefault();
  const payload = { name: $('#dashboardName').value.trim(), username: $('#dashboardUsername').value.trim() };
  if (!payload.name) return;
  await fetchJson('/api/accounts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  event.target.reset();
  await loadAccounts();
}

async function deleteAccount(slug) {
  try { await fetchJson(`/api/accounts/${encodeURIComponent(slug)}`, { method: 'DELETE' }); await loadAccounts(); }
  catch (error) { console.error(error); }
}

function runSearch(value) {
  const query = value.trim().toLowerCase();
  if (!query) return;
  const matches = (state.overview?.recent || []).filter((item) => JSON.stringify(item).toLowerCase().includes(query));
  $('#recordingsGrid').innerHTML = matches.length ? matches.map((item) => videoCard(item)).join('') : emptyState(`Aucun résultat pour « ${value} »`);
  document.querySelector('#recordings').scrollIntoView({ behavior: 'smooth' });
}

function setup() {
  $('#dashboardForm').addEventListener('submit', (event) => addAccount(event).catch(console.error));
  $('#dashboardAccounts').addEventListener('click', (event) => { const button = event.target.closest('[data-delete-account]'); if (button) deleteAccount(button.dataset.deleteAccount); });
  $('#addAccountButton').addEventListener('click', () => { $('.redesigned-form').classList.toggle('visible'); $('#dashboardName').focus(); });
  $('#globalSearch').addEventListener('keydown', (event) => { if (event.key === 'Enter') runSearch(event.target.value); });
  $('#aiSearchButton').addEventListener('click', () => runSearch($('#aiQuery').value));
  document.querySelectorAll('.ai-suggestions button').forEach((button) => button.addEventListener('click', () => { $('#aiQuery').value = button.textContent; runSearch(button.textContent); }));
  document.addEventListener('click', (event) => { const card = event.target.closest('[data-live-id]'); if (card?.dataset.liveId) window.location.href = `/?live=${encodeURIComponent(card.dataset.liveId)}`; });
}

setup();
loadOverview();
