(() => {
  const form = document.querySelector("[data-registration-form]");
  if (!form) return;

  const hiddenMode = form.querySelector("[name='identifier_type']");
  const modeRadios = Array.from(form.querySelectorAll("[name='identifier_mode_ui']"));
  const emailGroup = form.querySelector("[data-registration-email-group]");
  const phoneGroup = form.querySelector("[data-registration-phone-group]");
  const emailInput = form.querySelector("[name='email']");
  const phoneInput = form.querySelector("[name='phone_e164']");
  const passwordInput = form.querySelector("[name='password1']");
  const confirmInput = form.querySelector("[name='password2']");
  const strength = form.querySelector("[data-password-strength]");
  const matchStatus = form.querySelector("[data-password-match]");
  const submitButton = form.querySelector("[data-registration-submit]");
  const submitLabel = form.querySelector("[data-registration-submit-label]");
  let submitted = false;

  const setIdentifierMode = (mode) => {
    const useEmail = mode === "email";
    if (hiddenMode) hiddenMode.value = useEmail ? "email" : "phone";
    if (emailGroup) emailGroup.hidden = !useEmail;
    if (phoneGroup) phoneGroup.hidden = useEmail;
    if (emailInput) emailInput.disabled = !useEmail;
    if (phoneInput) phoneInput.disabled = useEmail;
  };

  modeRadios.forEach((radio) => {
    radio.addEventListener("change", () => {
      if (radio.checked) setIdentifierMode(radio.value);
    });
  });

  const firstMode = modeRadios.find((radio) => radio.checked);
  setIdentifierMode(firstMode?.value || "email");

  form.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = document.getElementById(button.dataset.passwordToggle);
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show
        ? `Hide ${input.name === "password2" ? "confirm password" : "password"}`
        : `Show ${input.name === "password2" ? "confirm password" : "password"}`);
      button.querySelector("span").textContent = show ? "Hide" : "Show";
    });
  });

  const setStrength = () => {
    if (!passwordInput || !strength) return;
    const value = passwordInput.value;
    if (!value) {
      strength.dataset.level = "";
      strength.querySelector("p").textContent =
        "Strength is advisory; server rules remain authoritative.";
      return;
    }

    let score = 0;
    if (value.length >= 8) score += 1;
    if (value.length >= 12) score += 1;
    if (/[a-z]/.test(value) && /[A-Z]/.test(value)) score += 1;
    if (/[0-9]/.test(value)) score += 1;
    if (/[^A-Za-z0-9]/.test(value)) score += 1;

    let level = "weak";
    let label = "Weak";
    if (score >= 4) {
      level = "fair";
      label = "Fair";
    }
    if (score >= 5 && value.length >= 12) {
      level = "strong";
      label = "Strong";
    }
    strength.dataset.level = level;
    strength.querySelector("p").textContent =
      `${label} (advisory only; server validation is final).`;
  };

  const setMatch = () => {
    if (!passwordInput || !confirmInput || !matchStatus) return;
    if (!confirmInput.value) {
      matchStatus.textContent = "";
      delete matchStatus.dataset.match;
      return;
    }
    if (passwordInput.value === confirmInput.value) {
      matchStatus.textContent = "Passwords match.";
      matchStatus.dataset.match = "yes";
    } else {
      matchStatus.textContent = "Passwords do not match.";
      matchStatus.dataset.match = "no";
    }
  };

  passwordInput?.addEventListener("input", () => {
    setStrength();
    setMatch();
  });
  confirmInput?.addEventListener("input", setMatch);

  form.addEventListener("submit", (event) => {
    if (submitted) {
      event.preventDefault();
      return;
    }
    submitted = true;
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.classList.add("is-loading");
      submitButton.setAttribute("aria-busy", "true");
    }
    if (submitLabel) submitLabel.textContent = "Creating account…";
  });

  const summary = document.querySelector("[data-registration-error-summary]");
  if (summary) {
    form.querySelectorAll(".registration-field-error").forEach((error) => {
      const field = (error.id
        ? document.getElementById(`id_${error.id.replace(/_error$/, "")}`)
        : null)
        || error.closest(".registration-field")?.querySelector("input, select");
      if (field) {
        field.setAttribute("aria-invalid", "true");
        if (error.id) {
          const describedBy = new Set(
            (field.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean)
          );
          describedBy.add(error.id);
          field.setAttribute("aria-describedby", Array.from(describedBy).join(" "));
        }
      }
    });
    summary.focus();
  }
})();
