"use strict";

const search = document.querySelector("#item-search");
if (search) {
  const rows = [...document.querySelectorAll("[data-item-name]")];
  const status = document.querySelector("#search-status");
  search.addEventListener("input", () => {
    const query = search.value.trim().toLocaleLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      row.hidden = !row.dataset.itemName.toLocaleLowerCase().includes(query);
      if (!row.hidden) visible += 1;
    });
    status.textContent = visible === 0
      ? "No matching items. Try a different search."
      : `${visible} of ${rows.length} items shown`;
  });
}

document.querySelectorAll("form[data-confirm-delete]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("Delete this item? This cannot be undone.")) {
      event.preventDefault();
    }
  });
});
