const insightOverlay = document.querySelector("[data-insight-info-overlay]");
const insightTitle = document.querySelector("[data-insight-info-title]");
const insightResearch = document.querySelector("[data-insight-info-research]");
const insightAction = document.querySelector("[data-insight-info-action]");
const insightCloseControls = document.querySelectorAll("[data-insight-info-close]");

function closeInsightModal() {
  if (!insightOverlay) return;

  insightOverlay.dataset.open = "false";
  insightOverlay.setAttribute("aria-hidden", "true");
}

document.querySelectorAll("[data-insight-info-trigger]").forEach((trigger) => {
  trigger.addEventListener("click", () => {
    if (!insightOverlay || !insightTitle || !insightResearch || !insightAction) {
      return;
    }

    insightTitle.textContent = trigger.dataset.insightTitle || "";
    insightResearch.textContent = trigger.dataset.insightResearch || "";
    insightAction.textContent = trigger.dataset.insightAction || "";
    insightOverlay.dataset.open = "true";
    insightOverlay.setAttribute("aria-hidden", "false");
  });
});

insightCloseControls.forEach((control) => {
  control.addEventListener("click", closeInsightModal);
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeInsightModal();
  }
});
