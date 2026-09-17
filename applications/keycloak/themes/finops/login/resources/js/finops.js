// Only layout crosses the frame boundary. Credentials remain in native Keycloak forms.
(() => {
  const embedded = window.parent !== window;
  if (embedded) document.documentElement.classList.add('finops-embedded');
  // The host morphs the panel. Nested cross-document snapshots can blank an iframe.
  window.addEventListener('pagereveal', event => {
    if (embedded) event.viewTransition?.skipTransition();
  });
  document.addEventListener('DOMContentLoaded', () => {
    const page = document.querySelector('.login-pf-page');
    const panel = document.querySelector('.card-pf');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    // Native cross-document transitions preserve form actions, errors and password managers.
    // Keyboard navigation stays immediate, as does reduced-motion navigation.
    document.addEventListener('keydown', () => document.documentElement.classList.add('keyboard-navigation'));
    document.addEventListener('pointerdown', () => document.documentElement.classList.remove('keyboard-navigation'));
    if (!page || !embedded) return;
    let parentOrigin;
    const allowed = ['https://app.sniper541.com', 'http://localhost:5173'];
    const notify = () => {
      if (parentOrigin) parent.postMessage({ type: 'finops-auth-layout', height: Math.ceil(page.getBoundingClientRect().height), mode: document.querySelector('#kc-register-form') ? 'register' : 'login' }, parentOrigin);
    };
    window.addEventListener('message', event => {
      if (event.source !== parent || !allowed.includes(event.origin) || event.data?.type !== 'finops-auth-host') return;
      parentOrigin = event.origin;
      notify();
    });
    document.addEventListener('click', event => {
      const link = event.target instanceof Element && event.target.closest('.finops-tabs a, #kc-form-options a, #kc-registration a');
      if (parentOrigin && event.detail > 0 && link && !event.ctrlKey && !event.metaKey && !event.shiftKey && !reduced.matches) {
        parent.postMessage({ type: 'finops-auth-transition' }, parentOrigin);
      }
    });
    new ResizeObserver(notify).observe(page);
    notify();
    // Keep the form stable while typing; motion is limited to page/mode changes.
    if (panel && reduced.matches) panel.style.animation = 'none';
  });
})();
