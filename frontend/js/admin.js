const burgerToggle = document.getElementById("burgerToggle");
const tabBar = document.querySelector(".tab-bar");

// cek state tersimpan
if (window.innerWidth > 992 && localStorage.getItem('sidebarState') === 'closed') {
    document.body.classList.add('sidebar-closed');
}

burgerToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    if (window.innerWidth > 992) {
        document.body.classList.toggle("sidebar-closed");
        const isClosed = document.body.classList.contains("sidebar-closed");
        localStorage.setItem("sidebarState", isClosed ? "closed" : "open");
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
        if (localStorage.getItem("sidebarState") === "closed") {
            document.body.classList.add("sidebar-closed");
        }
    } else {
        document.body.classList.remove("sidebar-closed");
    }
});


// logout button 
const logoutButton = document.querySelector('.btn-logout');

if (logoutButton) {
    logoutButton.addEventListener('click', () => {
        localStorage.removeItem('trioSaungSession');
        window.location.href = '/frontend/index.html';
    });
}

// logika clear button search
const searchInput = document.querySelector('#menuSearch');
const clearButton = document.querySelector('.clear');

searchInput.addEventListener('input', () => {
    clearButton.hidden = searchInput.value.length === 0;
});

clearButton.addEventListener('click', () => {
    searchInput.value = '';
    searchInput.focus();
    searchInput.dispatchEvent(new Event('input', { bubbles: true }));
});

