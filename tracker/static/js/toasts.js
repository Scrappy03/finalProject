document.querySelectorAll('[data-toast]').forEach((toast) => {
  window.setTimeout(() => {
    toast.classList.add('opacity-0', 'translate-x-4');
  }, 2500);

  window.setTimeout(() => {
    toast.remove();
  }, 3100);
});
