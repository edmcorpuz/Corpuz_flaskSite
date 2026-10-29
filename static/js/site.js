"use strict";

document.querySelectorAll("form[data-confirm-delete]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm("Delete this item? This cannot be undone.")) {
      event.preventDefault();
    }
  });
});
