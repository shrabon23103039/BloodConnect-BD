"use strict";

document.querySelectorAll("[data-google-oauth-form]").forEach((form) => {
  form.addEventListener("submit", () => {
    const associatedControl = Array.from(
      document.querySelectorAll("[data-google-oauth-control]")
    ).find((control) => control.dataset.googleOauthControl === form.id);
    const button = form.querySelector("button[type='submit']")
      || associatedControl?.querySelector("button[form='" + form.id + "']");
    const label = button?.querySelector("[data-google-oauth-label]")
      || form.querySelector("[data-google-oauth-label]");
    const status = form.querySelector("[data-google-oauth-status]")
      || associatedControl?.querySelector("[data-google-oauth-status]");
    if (!button || button.disabled) return;

    button.disabled = true;
    button.setAttribute("aria-busy", "true");
    if (label) label.textContent = "Connecting to Google…";
    if (status) status.textContent = "Connecting to Google. Please wait.";
  });
});
