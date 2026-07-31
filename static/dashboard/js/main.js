(function () {
  if (window.lucide) {
    lucide.createIcons();
  }

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

  var btn = document.getElementById("sidebar-toggle");
  var sidebar = document.getElementById("dashboard__sidebar");
  var backdrop = document.getElementById("sidebar-backdrop");
  if (!btn || !sidebar || !backdrop) return;

  function openSidebar() {
    sidebar.classList.remove("-translate-x-full");
    backdrop.classList.remove("hidden");
  }

  function closeSidebar() {
    sidebar.classList.add("-translate-x-full");
    backdrop.classList.add("hidden");
  }

  btn.addEventListener("click", function () {
    if (sidebar.classList.contains("-translate-x-full")) {
      openSidebar();
    } else {
      closeSidebar();
    }
  });

  backdrop.addEventListener("click", closeSidebar);
})();
