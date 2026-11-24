(() => {
  "use strict";

  const drawer = document.querySelector("#mobile-app-navigation");
  if (!drawer) {
    return;
  }

  drawer.querySelectorAll("a.app-nav-link[data-bs-dismiss='offcanvas']").forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      const destination = link.href;
      const offcanvas = window.bootstrap?.Offcanvas.getInstance(drawer);
      offcanvas?.hide();
      window.location.assign(destination);
    });
  });

  drawer.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      const offcanvas = window.bootstrap?.Offcanvas.getInstance(drawer);
      if (offcanvas) {
        event.preventDefault();
        offcanvas.hide();
        document.querySelector(".app-menu-toggle")?.focus();
      }
    }
  });
})();
