(() => {
  const codeInput = document.querySelector("[data-one-time-code]");
  const status = document.querySelector("[data-otp-paste-status]");
  if (!codeInput || !status) return;

  const clearPasteFeedback = () => {
    status.textContent = "";
    codeInput.removeAttribute("aria-invalid");
  };

  codeInput.addEventListener("input", clearPasteFeedback);
  codeInput.addEventListener("paste", (event) => {
    const clipboardText = event.clipboardData?.getData("text") || "";
    const candidates = Array.from(
      clipboardText.matchAll(/(^|[^0-9])([0-9]{6})(?![0-9])/g),
      (match) => match[2]
    );
    const isBareCode = /^[0-9]{6}$/.test(clipboardText.trim());

    if (candidates.length === 1 && !isBareCode) {
      event.preventDefault();
      codeInput.value = candidates[0];
      codeInput.dispatchEvent(new Event("input", {bubbles: true}));
      status.textContent = "One six-digit code was filled. Review it, then submit.";
      return;
    }

    if (candidates.length > 1 || (!isBareCode && clipboardText.trim())) {
      event.preventDefault();
      codeInput.value = "";
      codeInput.setAttribute("aria-invalid", "true");
      status.textContent = candidates.length > 1
        ? "This message contains more than one six-digit code. Copy and paste only the correct code."
        : "No single six-digit code was found. Enter or paste one six-digit code.";
    }
  });
})();
