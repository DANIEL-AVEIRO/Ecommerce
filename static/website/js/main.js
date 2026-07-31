(function () {
  if (window.lucide) {
    lucide.createIcons();
  }

  document.querySelectorAll("details.accordion").forEach(function (details) {
    var summary = details.querySelector("summary");
    var body = details.querySelector(".accordion__body");
    if (!summary || !body) return;

    if (details.open) {
      body.classList.add("is__open");
    }

    summary.addEventListener("click", function (event) {
      event.preventDefault();
      if (details.dataset.animating === "1") return;
      details.dataset.animating = "1";

      function finish() {
        details.dataset.animating = "0";
      }

      if (details.open) {
        body.classList.remove("is__open");
        var onClose = function (e) {
          if (e.target !== body || e.propertyName !== "grid-template-rows") return;
          body.removeEventListener("transitionend", onClose);
          details.removeAttribute("open");
          finish();
        };
        body.addEventListener("transitionend", onClose);
      } else {
        details.setAttribute("open", "");
        requestAnimationFrame(function () {
          body.classList.add("is__open");
        });
        var onOpen = function (e) {
          if (e.target !== body || e.propertyName !== "grid-template-rows") return;
          body.removeEventListener("transitionend", onOpen);
          finish();
        };
        body.addEventListener("transitionend", onOpen);
      }
    });
  });

  document.querySelectorAll("[data-toast]").forEach(function (toast) {
    function dismiss() {
      if (toast.classList.contains("is__leaving")) return;
      toast.classList.add("is__leaving");
      toast.addEventListener(
        "animationend",
        function () {
          toast.remove();
          var root = document.getElementById("toast-root");
          if (root && !root.querySelector("[data-toast]")) {
            root.remove();
          }
        },
        { once: true }
      );
    }

    var closeBtn = toast.querySelector("[data-toast-close]");
    if (closeBtn) {
      closeBtn.addEventListener("click", dismiss);
    }

    setTimeout(dismiss, 4500);
  });

  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
        btn.disabled = true;
        btn.classList.add("opacity-60", "pointer-events-none");
      });
      document.querySelectorAll('button[type="submit"][form="' + form.id + '"]').forEach(function (btn) {
        btn.disabled = true;
        btn.classList.add("opacity-60", "pointer-events-none");
      });
    });
  });
})();
