document.addEventListener("DOMContentLoaded", function () {
  const filter = document.querySelector("[data-request-status-filter]");
  const list = document.querySelector("[data-request-list]");
  if (!filter || !list) return;

  const rows = Array.from(list.querySelectorAll("[data-request-row]"));
  const count = document.querySelector("[data-request-visible-count]");
  const empty = document.querySelector("[data-request-filter-empty]");
  const statuses = Array.from(new Set(rows.map(function (row) {
    return row.dataset.requestStatus;
  }))).sort();

  statuses.forEach(function (status) {
    const option = document.createElement("option");
    option.value = status;
    option.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    filter.appendChild(option);
  });

  filter.addEventListener("change", function () {
    let visibleCount = 0;
    rows.forEach(function (row) {
      const visible = filter.value === "all" || row.dataset.requestStatus === filter.value;
      row.hidden = !visible;
      if (visible) visibleCount += 1;
    });
    if (count) count.textContent = String(visibleCount);
    if (empty) empty.hidden = visibleCount !== 0;
  });
});
