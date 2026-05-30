document.addEventListener("DOMContentLoaded", () => {

    console.log("✅ JS Loaded");

    // ======================
    // THEME TOGGLE (FINAL + SAFE)
    // ======================
    const themeBtn = document.getElementById("themeBtn");
    const themeIcon = document.getElementById("themeIcon");

    if (themeBtn && themeIcon) {

        const savedTheme = localStorage.getItem("theme");

        // 🔥 LOAD THEME
        if (savedTheme === "dark") {
            document.body.classList.add("dark-mode");

            themeIcon.classList.remove("fa-moon");
            themeIcon.classList.add("fa-sun");
        } else {
            document.body.classList.remove("dark-mode");

            themeIcon.classList.remove("fa-sun");
            themeIcon.classList.add("fa-moon");
        }

        // 🔥 TOGGLE THEME
        themeBtn.addEventListener("click", () => {

            document.body.classList.toggle("dark-mode");

            if (document.body.classList.contains("dark-mode")) {
                localStorage.setItem("theme", "dark");

                themeIcon.classList.remove("fa-moon");
                themeIcon.classList.add("fa-sun");
            } else {
                localStorage.setItem("theme", "light");

                themeIcon.classList.remove("fa-sun");
                themeIcon.classList.add("fa-moon");
            }
        });
    }

    // ======================
    // SIDEBAR TOGGLE
    // ======================
    const toggleBtn = document.getElementById("toggleBtn");
    const sidebar = document.getElementById("sidebar");

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener("click", () => {
            sidebar.classList.toggle("collapsed");
        });
    }

    // ======================
    // LOADER FIX
    // ======================
    const addForm = document.getElementById("addForm");
    const loader = document.getElementById("loader");

    if (addForm && loader) {
        addForm.addEventListener("submit", () => {
            loader.style.display = "block";
        });
    }

});