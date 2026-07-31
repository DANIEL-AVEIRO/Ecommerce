(function () {
  var main = document.getElementById("main-image");
  var modal = document.getElementById("gallery-modal");
  var full = document.getElementById("gallery-full");
  var openBtn = document.getElementById("open-gallery");
  var closeBtn = document.getElementById("close-gallery");
  if (!main || !modal || !full) return;

  document.querySelectorAll(".gallery__thumb").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var url = btn.getAttribute("data-full");
      main.src = url;
    });
  });

  function openGallery() {
    full.src = main.src;
    modal.classList.remove("hidden");
    modal.classList.add("flex");
  }

  function closeGallery() {
    modal.classList.add("hidden");
    modal.classList.remove("flex");
  }

  if (openBtn) openBtn.addEventListener("click", openGallery);
  if (closeBtn) closeBtn.addEventListener("click", closeGallery);
  modal.addEventListener("click", function (e) {
    if (e.target === modal) closeGallery();
  });
})();
