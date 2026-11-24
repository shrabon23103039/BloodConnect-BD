"use strict";

document.addEventListener("DOMContentLoaded", () => {
  const identifier = document.querySelector(".login-form input[name='username']");
  const password = document.querySelector(".login-form input[name='password']");

  if (identifier) {
    if (!identifier.hasAttribute("placeholder")) identifier.setAttribute("placeholder", "Email or phone");
  }
  if (password && !password.hasAttribute("placeholder")) {
    password.setAttribute("placeholder", "Enter your password");
  }
});
