document.querySelectorAll('[data-range-output]').forEach((output) => {
  const input = document.getElementById(output.dataset.rangeOutput);
  if (!input) return;

  const sync = () => {
    output.textContent = input.value || '5';
  };

  input.addEventListener('input', sync);
  sync();
});

const screenTimeInput = document.getElementById('id_evening_screen_time');
const screenTimeButtons = document.querySelectorAll('[data-screen-value]');

function setScreenTime(value) {
  if (!screenTimeInput) return;

  screenTimeInput.value = value;
  screenTimeButtons.forEach((button) => {
    const isActive = button.dataset.screenValue === value;
    button.classList.toggle('bg-primary', isActive);
    button.classList.toggle('text-on-primary', isActive);
    button.classList.toggle('border-primary', isActive);
    button.classList.toggle('shadow-sm', isActive);
    button.classList.toggle('bg-surface-container-low', !isActive);
    button.classList.toggle('text-on-surface-variant', !isActive);
    button.classList.toggle('border-outline-variant', !isActive);
  });
}

screenTimeButtons.forEach((button) => {
  button.addEventListener('click', () => setScreenTime(button.dataset.screenValue));
});

if (screenTimeInput?.value) {
  setScreenTime(screenTimeInput.value);
}

const caffeineToggle = document.getElementById('id_caffeine_consumed');
const caffeineTimeInput = document.getElementById('id_latest_caffeine_time');
const caffeineTimePanel = document.querySelector('[data-caffeine-time-panel]');

function syncCaffeineTime() {
  if (!caffeineToggle || !caffeineTimeInput || !caffeineTimePanel) return;

  const isEnabled = caffeineToggle.checked;
  caffeineTimeInput.disabled = !isEnabled;
  caffeineTimeInput.required = isEnabled;
  if (!isEnabled) {
    caffeineTimeInput.value = '';
  }
  caffeineTimePanel.classList.toggle('opacity-40', !isEnabled);
  caffeineTimePanel.classList.toggle('pointer-events-none', !isEnabled);
}

caffeineToggle?.addEventListener('change', syncCaffeineTime);
syncCaffeineTime();

const moodInput = document.getElementById('id_mood_rating');
const moodButtons = document.querySelectorAll('[data-mood-value]');

function setMood(value) {
  if (!moodInput) return;

  moodInput.value = value;
  moodButtons.forEach((button) => {
    const isActive = button.dataset.moodValue === String(value);
    button.classList.toggle('bg-surface-container-low', isActive);
    button.classList.toggle('border-primary', isActive);
    button.classList.toggle('shadow-sm', isActive);
    button.querySelectorAll('span').forEach((span) => {
      span.classList.toggle('text-primary', isActive);
      span.classList.toggle('text-on-surface-variant', !isActive);
    });
  });
}

moodButtons.forEach((button) => {
  button.addEventListener('click', () => setMood(button.dataset.moodValue));
});

setMood(moodInput?.value || '6');
