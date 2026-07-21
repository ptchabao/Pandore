const dashboardAccounts = document.querySelector('#dashboardAccounts');
const dashboardForm = document.querySelector('#dashboardForm');
const dashboardName = document.querySelector('#dashboardName');
const dashboardUsername = document.querySelector('#dashboardUsername');

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  return response.json();
}

function renderAccounts(accounts) {
  dashboardAccounts.innerHTML = accounts.map(account => `
    <div class="account-item">
      <div class="account-meta">
        <div class="account-avatar">${(account.avatar || account.name || 'PA').slice(0, 2).toUpperCase()}</div>
        <div>
          <strong>${account.name}</strong><br />
          <small>@${account.username || account.creatorSlug}</small>
        </div>
      </div>
      <button class="icon-button" data-delete-account="${account.creatorSlug}">Retirer</button>
    </div>
  `).join('');
}

async function loadAccounts() {
  const overview = await fetchJson('/api/overview');
  renderAccounts(overview.accounts || []);
}

async function addAccount(event) {
  event.preventDefault();
  const payload = {
    name: dashboardName.value.trim(),
    username: dashboardUsername.value.trim()
  };
  if (!payload.name) return;
  const response = await fetchJson('/api/accounts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (response.ok) {
    dashboardForm.reset();
    await loadAccounts();
  }
}

async function deleteAccount(slug) {
  const response = await fetchJson(`/api/accounts/${slug}`, { method: 'DELETE' });
  if (response.ok) {
    await loadAccounts();
  }
}

dashboardAccounts.addEventListener('click', async (event) => {
  const target = event.target.closest('[data-delete-account]');
  if (!target) return;
  await deleteAccount(target.dataset.deleteAccount);
});

dashboardForm.addEventListener('submit', addAccount);
loadAccounts();
