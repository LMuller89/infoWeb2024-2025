// Smooth Scrolling
$("#navbar a, .btn").on("click", function (event) {
  if (this.hash !== "") {
    event.preventDefault();

    const hash = this.hash;

    $("html, body").animate(
      {
        scrollTop: $(hash).offset().top - 100,
      },
      800
    );
  }
});

// Sticky menu background
window.addEventListener("scroll", function () {
  if (window.scrollY > 150) {
    document.querySelector("#navbar").style.opacity = 0.9;
  } else {
    document.querySelector("#navbar").style.opacity = 1;
  }
});

function openModal(imgElement) {
  var modal = document.getElementById("modal");
  var fullImage = document.getElementById("full-image");

  fullImage.src = imgElement.src;
  modal.style.display = "flex";
}

function closeModal() {
  document.getElementById("modal").style.display = "none";
}
