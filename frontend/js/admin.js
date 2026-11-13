// logic CRUD laporan, menu, edit
const burgerToggle = document.getElementById("burgerToggle");
const tabBar = document.querySelector(".tab-bar");

burgerToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    if (window.innerWidth > 992) {
        document.body.classList.toggle("sidebar-closed");
    } else {
        document.body.classList.toggle("sidebar-open");
    }
});

document.addEventListener("click", (e) => {
    if (
        window.innerWidth <= 992 &&
        document.body.classList.contains("sidebar-open") &&
        !tabBar.contains(e.target) &&
        !burgerToggle.contains(e.target)
    ) {
        document.body.classList.remove("sidebar-open");
    }
});

window.addEventListener("resize", () => {
    if (window.innerWidth > 992) {
        document.body.classList.remove("sidebar-open");
    } else {
        document.body.classList.remove("sidebar-closed");
    }
});