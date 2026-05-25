const weeklyGoalInput = document.getElementById('id_weekly_exercise_goal');

document.querySelectorAll('[data-step-goal]').forEach((button) => {
  button.addEventListener('click', () => {
    if (!weeklyGoalInput) return;

    const step = Number(button.dataset.stepGoal);
    const currentValue = Number(weeklyGoalInput.value || 0);
    weeklyGoalInput.value = Math.max(0, Math.min(7, currentValue + step));
  });
});
