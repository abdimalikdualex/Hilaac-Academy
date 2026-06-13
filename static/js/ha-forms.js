/**
 * Hilaac Academy — lightweight form UX (no dependencies).
 * - Prevents duplicate submissions
 * - Shows loading state on submit buttons
 * - Confirmation dialogs for destructive actions
 */
(function () {
  "use strict";

  function busySubmit(form) {
    var submits = form.querySelectorAll("button[type='submit'], input[type='submit']");
    submits.forEach(function (btn) {
      if (btn.disabled || btn.dataset.noBusy === "true") return;
      btn.disabled = true;
      if (!btn.dataset.originalText) {
        btn.dataset.originalText = btn.tagName === "INPUT" ? btn.value : btn.textContent;
      }
      var loading = btn.dataset.loadingText || "Saving...";
      if (btn.tagName === "INPUT") btn.value = loading;
      else btn.textContent = loading;
    });
    form.classList.add("ha-form-busy");
  }

  document.addEventListener("submit", function (e) {
    var form = e.target;
    if (!form || form.tagName !== "FORM") return;

    var confirmMsg = form.getAttribute("data-confirm");
    if (confirmMsg && form.dataset.confirmed !== "1") {
      e.preventDefault();
      if (window.confirm(confirmMsg)) {
        form.dataset.confirmed = "1";
        if (typeof form.requestSubmit === "function") form.requestSubmit();
        else form.submit();
      }
      return;
    }

    if (form.classList.contains("ha-form-busy")) {
      e.preventDefault();
      return;
    }
    busySubmit(form);
  });

  document.addEventListener("click", function (e) {
    var link = e.target.closest("a[data-confirm]");
    if (!link) return;
    var msg = link.getAttribute("data-confirm");
    if (msg && !window.confirm(msg)) e.preventDefault();
  });
})();
