document.addEventListener("DOMContentLoaded", () => {
    // search bar & clear button
    const searchInput = document.querySelector("#menuSearch");
    const clearButton = document.querySelector(".clear");

    if (searchInput && clearButton) {
        searchInput.addEventListener("input", () => {
            clearButton.hidden = searchInput.value.length === 0;
        });

        clearButton.addEventListener("click", () => {
            searchInput.value = "";
            searchInput.focus();
            searchInput.dispatchEvent(new Event("input", { bubbles: true }));
        });
    }

    // state, elemen modal & tabel menu
    let daftarMenu = [];
    let editingMenuId = null;
    let deletingMenuId = null;

    const menuTableBody = document.getElementById("isi-tabel");
    const menuModal = document.getElementById("menuModal");
    const openMenuModalBtn = document.getElementById("openMenuModal");
    const formTambahMenu = document.getElementById("formTambahMenu");

    if (!menuModal || !openMenuModalBtn || !formTambahMenu || !menuTableBody) return;

    const closeModalButtons = menuModal.querySelectorAll(".js-close-modal");
    const modalTitle = document.getElementById("modalTitle");
    const modalSubtitle = menuModal.querySelector("p");
    const submitBtn = formTambahMenu.querySelector(".simpan-btn");

    const nameInput = document.getElementById("menuName") || formTambahMenu.querySelector('[name="menuName"]');
    const categoryInput = document.getElementById("menuCategory");
    const priceInput = document.getElementById("menuPrice");
    const descInput = document.getElementById("menuDescription");
    const imageInput = document.getElementById("menuImage");
    const spiceInput = document.getElementById("hasSpiceLevel");
    const recommendedInput = document.getElementById("isRecommended");
    const availableInput = document.getElementById("isAvailable");
    const statusGroup = document.getElementById("statusGroup");

    // Elemen Modal Popup Delete
    const deleteModal = document.getElementById("deleteModal");
    const deleteModalText = document.getElementById("deleteModalText");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");

    // render tabel daftar menu
    function renderMenuTable(data) {
        menuTableBody.innerHTML = "";

        if (data.length === 0) {
            menuTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        Belum ada menu yang ditambahkan. Klik <strong>+ Tambah Menu</strong> untuk mulai.
                    </td>
                </tr>
            `;
            return;
        }

        data.forEach((menu) => {
            const kategoriLabel = menu.menuCategory.charAt(0).toUpperCase() + menu.menuCategory.slice(1);
            const hargaLabel = `Rp ${Number(menu.menuPrice).toLocaleString("id-ID")}`;

            const statusHTML = menu.isAvailable
                ? `<div class="tersedia">Tersedia</div>`
                : `<div class="tak-tersedia">Tidak Tersedia</div>`;

            const rekomendasiHTML = menu.isRecommended
                ? `<span class="fire" title="Menu Rekomendasi"></span>`
                : `<span>-</span>`;

            const row = `
                <tr class="baris-menu" data-id="${menu.id}">
                    <td>
                        <div class="info-menu">
                            <div class="gambar">
                                <img src="${menu.menuImage}" alt="${menu.menuName}" class="foto-menu">
                            </div>
                            <span class="nama-menu">${menu.menuName}</span>
                        </div>
                    </td>
                    <td>${kategoriLabel}</td>
                    <td>${hargaLabel}</td>
                    <td>
                        <div class="ketersediaan">${statusHTML}</div>
                    </td>
                    <td>
                        <div class="aksi">${rekomendasiHTML}</div>
                    </td>
                    <td>
                        <div class="aksi">
                            <button type="button" class="btn-kelola btn-edit" data-id="${menu.id}" aria-label="Edit ${menu.menuName}">
                                <span class="edit"></span>
                            </button>
                            <button type="button" class="btn-kelola btn-delete" data-id="${menu.id}" aria-label="Hapus ${menu.menuName}">
                                <span class="delete"></span>
                            </button>
                        </div>
                    </td>
                </tr>
            `;

            menuTableBody.insertAdjacentHTML("beforeend", row);
        });
    }

    // buka tutup modal ()
    function resetModalToAddMode() {
        editingMenuId = null;
        formTambahMenu.reset();
        if (statusGroup) statusGroup.hidden = true;
        if (availableInput) availableInput.checked = true;
        imageInput.required = true;
        modalTitle.textContent = "Tambah Menu";
        modalSubtitle.textContent = "Lengkapi detail hidangan baru di bawah ini.";
        submitBtn.textContent = "Simpan Menu";
    }

    function openModal() {
        menuModal.classList.add("is-open");
        menuModal.setAttribute("aria-hidden", "false");
        if (nameInput) {
            setTimeout(() => nameInput.focus(), 50);
        }
    }

    function closeModal() {
        menuModal.classList.remove("is-open");
        menuModal.setAttribute("aria-hidden", "true");
        resetModalToAddMode();
    }

    function closeDeleteModal() {
        deletingMenuId = null;
        if (deleteModal) {
            deleteModal.classList.remove("is-open");
            deleteModal.setAttribute("aria-hidden", "true");
        }
    }

    // Buka modal dengan Tambah Menu
    openMenuModalBtn.addEventListener("click", () => {
        resetModalToAddMode();
        openModal();
    });

    // Tutup modal lewat tombol X / Batal / klik latar belakang / ESC
    closeModalButtons.forEach((btn) => btn.addEventListener("click", closeModal));

    menuModal.addEventListener("click", (e) => {
        if (e.target === menuModal) closeModal();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (menuModal.classList.contains("is-open")) closeModal();
            if (deleteModal && deleteModal.classList.contains("is-open")) closeDeleteModal();
        }
    });

    // format pemisah harga ribuan
    if (priceInput) {
        priceInput.addEventListener("input", function () {
            let rawValue = this.value.replace(/[^0-9]/g, "").replace(/^0+/, "");
            this.value = rawValue === "" ? "" : Number(rawValue).toLocaleString("id-ID");
        });
    }

    // submit form
    formTambahMenu.addEventListener("submit", function (e) {
        e.preventDefault();

        const fileFoto = imageInput.files[0];
        const rawPrice = Number(priceInput.value.replace(/[^0-9]/g, ""));
        const isRecommendedVal = recommendedInput ? recommendedInput.checked : false;
        const isAvailableVal = availableInput ? availableInput.checked : true;

        // tombol edit di daftar menu
        if (editingMenuId) {
            const index = daftarMenu.findIndex((m) => m.id === editingMenuId);
            if (index !== -1) {
                const oldMenu = daftarMenu[index];
                daftarMenu[index] = {
                    ...oldMenu,
                    menuName: nameInput.value.trim(),
                    menuCategory: categoryInput.value,
                    menuPrice: rawPrice,
                    menuDescription: descInput.value.trim(),
                    menuImage: fileFoto ? URL.createObjectURL(fileFoto) : oldMenu.menuImage,
                    hasSpiceLevel: spiceInput ? spiceInput.checked : false,
                    isRecommended: isRecommendedVal,
                    isAvailable: isAvailableVal
                };
            }
        } else {
            // tambah menu
            const newMenu = {
                id: "menu_" + Date.now(),
                menuName: nameInput.value.trim(),
                menuCategory: categoryInput.value,
                menuPrice: rawPrice,
                menuDescription: descInput.value.trim(),
                menuImage: fileFoto ? URL.createObjectURL(fileFoto) : "",
                hasSpiceLevel: spiceInput ? spiceInput.checked : false,
                isRecommended: isRecommendedVal,
                isAvailable: true
            };
            daftarMenu.push(newMenu);
        }

        renderMenuTable(daftarMenu);
        closeModal();
    });

    // tombol edit dan hapus di tabel daftar menu 
    menuTableBody.addEventListener("click", (e) => {
        const editBtn = e.target.closest(".btn-edit");
        const deleteBtn = e.target.closest(".btn-delete");

        if (editBtn) {
            const id = editBtn.dataset.id;
            const menu = daftarMenu.find((m) => m.id === id);
            if (!menu) return;

            editingMenuId = id;
            if (statusGroup) statusGroup.hidden = false;

            modalTitle.textContent = "Edit Menu";
            modalSubtitle.textContent = "Perbarui informasi, status stok, atau rekomendasi hidangan.";
            submitBtn.textContent = "Simpan Perubahan";

            nameInput.value = menu.menuName;
            categoryInput.value = menu.menuCategory;
            priceInput.value = Number(menu.menuPrice).toLocaleString("id-ID");
            descInput.value = menu.menuDescription || "";
            if (spiceInput) spiceInput.checked = menu.hasSpiceLevel;
            if (recommendedInput) recommendedInput.checked = menu.isRecommended;
            if (availableInput) availableInput.checked = menu.isAvailable;

            imageInput.value = "";
            imageInput.required = false;

            openModal();
        }

        // konfirmasi hapus popup view
        if (deleteBtn) {
            const id = deleteBtn.dataset.id;
            const menu = daftarMenu.find((m) => m.id === id);
            if (!menu) return;

            if (deleteModal && deleteModalText) {
                deletingMenuId = id;
                deleteModalText.innerHTML = `Apakah Anda yakin ingin menghapus <strong>${menu.menuName}</strong> dari daftar menu?`;
                deleteModal.classList.add("is-open");
                deleteModal.setAttribute("aria-hidden", "false");
            } else if (confirm(`Hapus menu "${menu.menuName}"?`)) {
                daftarMenu = daftarMenu.filter((m) => m.id !== id);
                renderMenuTable(daftarMenu);
            }
        }
    });

    // tutup dan konfirmasi popup modal delete
    if (deleteModal) {
        deleteModal.querySelectorAll(".js-close-delete").forEach((btn) => {
            btn.addEventListener("click", closeDeleteModal);
        });

        deleteModal.addEventListener("click", (e) => {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", () => {
            if (deletingMenuId) {
                daftarMenu = daftarMenu.filter((m) => m.id !== deletingMenuId);
                renderMenuTable(daftarMenu);
            }
            closeDeleteModal();
        });
    }

    // render awal saat katalog menu dibuka
    renderMenuTable(daftarMenu);
});