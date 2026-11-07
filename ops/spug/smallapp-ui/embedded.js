/* The native Spug route reuses this page on the same origin and session. */
(() => {
  'use strict';
  if (new URLSearchParams(window.location.search).get('embedded') !== '1') return;
  document.documentElement.classList.add('spug-embedded');
  // Login links created later must navigate the complete Spug window, never nest
  // a second login/layout inside the workspace. No base URL or token is changed.
  const base = document.createElement('base');
  base.target = '_top';
  document.head.append(base);
})();
