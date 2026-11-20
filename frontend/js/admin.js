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


// popup modal tambah menu
document.addEventListener('DOMContentLoaded', () => {
    const menuModal = document.getElementById('menuModal');
    const openMenuModalBtn = document.getElementById('openMenuModal');
    const formTambahMenu = document.getElementById('formTambahMenu');

    // Jalankan logika modal hanya jika elemen modal & tombolnya ada di halaman ini
    if (menuModal && openMenuModalBtn && formTambahMenu) {
        const closeModalButtons = menuModal.querySelectorAll('.js-close-modal');
        const priceInput = formTambahMenu.querySelector('input[name="menuPrice"]');
        const firstInput = formTambahMenu.querySelector('input[name="menuName"]');

        // fungsi Buka Modal
        function openModal() {
            menuModal.classList.add('is-open');
            menuModal.setAttribute('aria-hidden', 'false');
            
            // Otomatis fokus ke input Nama Menu saat modal terbuka
            if (firstInput) {
                setTimeout(() => firstInput.focus(), 50);
            }
        }

        // tutup modal
        function closeModal() {
            menuModal.classList.remove('is-open');
            menuModal.setAttribute('aria-hidden', 'true');
        }

        // tombol tambah menu
        openMenuModalBtn.addEventListener('click', openModal);

        // tombol batal
        closeModalButtons.forEach((btn) => {
            btn.addEventListener('click', closeModal);
        });

        // tutup popup modal jika tekan layar belakang diluar
        menuModal.addEventListener('click', (e) => {
            if (e.target === menuModal) {
                closeModal();
            }
        });

        // tutup popup modal jika tekan ESC 
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && menuModal.classList.contains('is-open')) {
                closeModal();
            }
        });

        // aturan pemisah angka ribuan
        if (priceInput) {
            priceInput.addEventListener('input', function () {
                let rawValue = this.value.replace(/[^0-9]/g, '');
                rawValue = rawValue.replace(/^0+/, '');

                if (rawValue === '') {
                    this.value = '';
                    return;
                }

                this.value = Number(rawValue).toLocaleString('id-ID');
            });
        }

        // fungsi submit
        formTambahMenu.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(this);
            const hargaMurni = priceInput ? Number(priceInput.value.replace(/[^0-9]/g, '')) : 0;

            const dataMenu = {
                nama: formData.get('menuName'),
                kategori: formData.get('menuCategory'),
                harga: hargaMurni,
                deskripsi: formData.get('menuDescription'),
                foto: formData.get('menuImage')
            };

            console.log('Data menu siap disimpan:', dataMenu);

            // reset dan tutup modal card setelah submit
            this.reset();
            closeModal();
        });
    }
});