// Keep keyboard navigation immediate during native page transitions.
document.addEventListener('keydown', () => document.documentElement.classList.add('keyboard-navigation'));
document.addEventListener('pointerdown', () => document.documentElement.classList.remove('keyboard-navigation'));
