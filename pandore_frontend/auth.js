const form = document.querySelector('#authForm');
const title = document.querySelector('#authTitle');
const subtitle = document.querySelector('#authSubtitle');
const submit = document.querySelector('#authSubmit');
const switchMode = document.querySelector('#switchMode');
const switchText = document.querySelector('#switchText');
const confirmLabel = document.querySelector('#confirmLabel');
const confirmInput = document.querySelector('#authConfirm');
const errorBox = document.querySelector('#authError');
let registerMode = window.location.pathname === '/register';

function renderMode() {
  title.textContent = registerMode ? 'Créez votre coffre Pandore' : 'Bienvenue dans Pandore';
  subtitle.textContent = registerMode ? 'Votre espace privé d’archives vidéo commence ici.' : 'Connectez-vous pour accéder à votre bibliothèque privée.';
  submit.innerHTML = registerMode ? 'Créer mon coffre <span>→</span>' : 'Se connecter <span>→</span>';
  switchText.textContent = registerMode ? 'Vous avez déjà un compte ?' : 'Nouveau sur Pandore ?';
  switchMode.textContent = registerMode ? 'Se connecter' : 'Créer un compte';
  confirmLabel.classList.toggle('hidden', !registerMode);
  confirmInput.required = registerMode;
}

switchMode.addEventListener('click', () => { registerMode = !registerMode; renderMode(); });
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorBox.textContent = '';
  if (registerMode && confirmInput.value !== document.querySelector('#authPassword').value) { errorBox.textContent = 'Les mots de passe ne correspondent pas.'; return; }
  const endpoint = registerMode ? '/api/auth/register' : '/api/auth/login';
  try {
    const response = await fetch(endpoint, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: document.querySelector('#authEmail').value, password: document.querySelector('#authPassword').value }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Impossible de continuer');
    window.location.href = '/dashboard';
  } catch (error) { errorBox.textContent = error.message; }
});
renderMode();
