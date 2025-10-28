const themeSwitch = document.getElementById("theme-switch");
const body = document.body;

// Check if user had a saved theme in localStorage
if (localStorage.getItem("theme") === "dark") {
  body.classList.add("darkmode");
}

// Toggle theme when clicking the switch
themeSwitch.addEventListener("click", () => {
  body.classList.toggle("darkmode");

  if (body.classList.contains("darkmode")) {
    localStorage.setItem("theme", "dark");
  } else {
    localStorage.setItem("theme", "light");
  }
});
