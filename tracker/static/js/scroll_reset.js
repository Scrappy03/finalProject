if ('scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual';
}

window.addEventListener('pageshow', () => {
  if (!window.location.hash) {
    window.requestAnimationFrame(() => window.scrollTo(0, 0));
  }
});
