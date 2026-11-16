const info = document.getElementById("project-info");
const trigger = document.getElementById("project-info-trigger");
const panel = document.getElementById("project-info-panel");
let pointerInside = false;
let closeTimer = null;

function show(open) {
  clearTimeout(closeTimer);
  closeTimer = null;
  panel.hidden = !open;
  trigger.setAttribute("aria-expanded", String(open));
}

info.addEventListener("pointerenter", () => {
  pointerInside = true;
  show(true);
});
info.addEventListener("pointerleave", () => {
  pointerInside = false;
  if (!info.contains(document.activeElement)) {
    closeTimer = setTimeout(() => {
      if (!pointerInside && !info.contains(document.activeElement)) show(false);
    }, 180);
  }
});
info.addEventListener("focusin", () => show(true));
info.addEventListener("focusout", event => {
  if (!pointerInside && !info.contains(event.relatedTarget)) show(false);
});
trigger.addEventListener("click", () => show(true));
document.addEventListener("pointerdown", event => {
  if (!info.contains(event.target)) show(false);
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && !panel.hidden) {
    if (panel.contains(document.activeElement)) trigger.focus();
    show(false);
  }
});
