document.addEventListener("DOMContentLoaded", () => {
    // state & elemen (daftar akun, edit, hapus)
    let daftarAkun = [];
    let editingAkunId = null;
    let deletingAkunId = null;

    const akunTableBody = document.getElementById("isi-tabel-akun");
    const akunModal = document.getElementById("akunModal");
    const openAkunModalBtn = document.getElementById("openAkunModal");
    const formTambahAkun = document.getElementById("formTambahAkun");

    if (!akunModal || !openAkunModalBtn || !formTambahAkun || !akunTableBody) return;

    const closeModalButtons = akunModal.querySelectorAll(".js-close-modal");
    const modalTitle = document.getElementById("modalTitle");
    const modalSubtitle = document.getElementById("modalSubtitle");
    const submitBtn = formTambahAkun.querySelector(".simpan-btn");

    // input di form tambah akun
    const emailInput = document.getElementById("akunEmail");
    const usernameInput = document.getElementById("akunUsername");
    const roleInput = document.getElementById("akunRole");
    const passwordInput = document.getElementById("akunPassword");
    const activeInput = document.getElementById("isActive");
    const statusGroup = document.getElementById("statusGroup");

    // elemen modal hapus
    const deleteAkunModal = document.getElementById("deleteAkunModal");
    const deleteModalText = document.getElementById("deleteModalText");
    const confirmDeleteBtn = document.getElementById("confirmDeleteBtn");

    // render tabel daftar akun
    function renderAkunTable(data) {
        akunTableBody.innerHTML = "";

        if (data.length === 0) {
            akunTableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="empty-state">
                        Belum ada akun pengguna yang ditambahkan. Klik <strong>+ Tambah Akun</strong> untuk mulai.
                    </td>
                </tr>
            `;
            return;
        }

        data.forEach((akun) => {
            const roleLabel = akun.role.charAt(0).toUpperCase() + akun.role.slice(1);

            const statusHTML = akun.isActive
                ? `<div class="tersedia">Aktif</div>`
                : `<div class="tak-tersedia">Nonaktif</div>`;

            // visible eye password
            const maskedPassword = "•".repeat(akun.password.length);

            const row = `
                <tr class="baris-menu" data-id="${akun.id}">
                    <td>${akun.email}</td>
                    <td>${akun.username}</td>
                    <td><span class="badge-role role-${akun.role}">${roleLabel}</span></td>
                    <td>
                        <div class="password-cell">
                            <span class="password-text" data-visible="false" data-password="${akun.password}">${maskedPassword}</span>
                            <button type="button" class="btn-kelola btn-toggle-pw" aria-label="Tampilkan atau sembunyikan kata sandi" title="Lihat kata sandi">
                                <span class="icon-eye"></span>
                            </button>
                        </div>
                    </td>
                    <td>
                        <div class="ketersediaan">${statusHTML}</div>
                    </td>
                    <td>
                        <div class="aksi">
                            <button type="button" class="btn-kelola btn-edit" data-id="${akun.id}" aria-label="Edit ${akun.username}">
                                <span class="edit"></span>
                            </button>
                            <button type="button" class="btn-kelola btn-delete" data-id="${akun.id}" aria-label="Hapus ${akun.username}">
                                <span class="delete"></span>
                            </button>
                        </div>
                    </td>
                </tr>
            `;

            akunTableBody.insertAdjacentHTML("beforeend", row);
        });
    }

    // pengaturan buka & tutup modal card (edit, hapus, tambah akun)
    function resetModalToAddMode() {
        editingAkunId = null;
        formTambahAkun.reset();
        if (statusGroup) statusGroup.hidden = true;
        if (activeInput) activeInput.checked = true;
        passwordInput.required = true;
        passwordInput.placeholder = "Minimal 6 karakter";
        modalTitle.textContent = "Tambah Akun";
        modalSubtitle.textContent = "Lengkapi detail akun staf atau admin baru di bawah ini.";
        submitBtn.textContent = "Simpan Akun";
    }

    function openModal() {
        akunModal.classList.add("is-open");
        akunModal.setAttribute("aria-hidden", "false");
        if (emailInput) {
            setTimeout(() => emailInput.focus(), 50);
        }
    }

    function closeModal() {
        akunModal.classList.remove("is-open");
        akunModal.setAttribute("aria-hidden", "true");
        resetModalToAddMode();
    }

    function closeDeleteModal() {
        deletingAkunId = null;
        if (deleteAkunModal) {
            deleteAkunModal.classList.remove("is-open");
            deleteAkunModal.setAttribute("aria-hidden", "true");
        }
    }

    // buka modal mode Tambah Akun
    openAkunModalBtn.addEventListener("click", () => {
        resetModalToAddMode();
        openModal();
    });

    // tutup modal lewat tombol X / Batal / klik latar belakang / ESC
    closeModalButtons.forEach((btn) => btn.addEventListener("click", closeModal));

    akunModal.addEventListener("click", (e) => {
        if (e.target === akunModal) closeModal();
    });

    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            if (akunModal.classList.contains("is-open")) closeModal();
            if (deleteAkunModal && deleteAkunModal.classList.contains("is-open")) closeDeleteModal();
        }
    });

    // submit form tambah akun & simpan hasil edit
    formTambahAkun.addEventListener("submit", (e) => {
        e.preventDefault();

        const emailVal = emailInput.value.trim().toLowerCase();
        const usernameVal = usernameInput.value.trim();
        const roleVal = roleInput.value;
        const passwordVal = passwordInput.value;
        const isActiveVal = activeInput ? activeInput.checked : true;

        // validasi untuk mencegah adanya duplikat email
        const isDuplicateEmail = daftarAkun.some(
            (akun) => akun.email === emailVal && akun.id !== editingAkunId
        );
        if (isDuplicateEmail) {
            alert("Email ini sudah terdaftar pada akun lain.");
            emailInput.focus();
            return;
        }

        // edit akun
        if (editingAkunId) {
            const index = daftarAkun.findIndex((a) => a.id === editingAkunId);
            if (index !== -1) {
                const oldAkun = daftarAkun[index];
                daftarAkun[index] = {
                    ...oldAkun,
                    email: emailVal,
                    username: usernameVal,
                    role: roleVal,
                    // masih menyimpan password lama, jika tidak diedit
                    password: passwordVal !== "" ? passwordVal : oldAkun.password,
                    isActive: isActiveVal
                };
            }
        } else {
            // tambah akun baru 
            const newAkun = {
                id: "user_" + Date.now(),
                email: emailVal,
                username: usernameVal,
                role: roleVal,
                password: passwordVal,
                isActive: true 
            };
            daftarAkun.push(newAkun);
        }

        renderAkunTable(daftarAkun);
        closeModal();
    });

    // kelola dalam daftar tabel akun (edit, hapus, lihat password)
    akunTableBody.addEventListener("click", (e) => {
        const togglePwBtn = e.target.closest(".btn-toggle-pw");
        const editBtn = e.target.closest(".btn-edit");
        const deleteBtn = e.target.closest(".btn-delete");

        // lihat kata sandi
        if (togglePwBtn) {
            const cell = togglePwBtn.closest(".password-cell");
            const pwSpan = cell.querySelector(".password-text");
            const rawPassword = pwSpan.dataset.password;
            const isVisible = pwSpan.dataset.visible === "true";

            if (isVisible) {
                pwSpan.textContent = "•".repeat(rawPassword.length);
                pwSpan.dataset.visible = "false";
                togglePwBtn.classList.remove("is-visible");
            } else {
                pwSpan.textContent = rawPassword;
                pwSpan.dataset.visible = "true";
                togglePwBtn.classList.add("is-visible");
            }
            return;
        }

        // edit akun
        if (editBtn) {
            const id = editBtn.dataset.id;
            const akun = daftarAkun.find((a) => a.id === id);
            if (!akun) return;

            editingAkunId = id;
            if (statusGroup) statusGroup.hidden = false;

            modalTitle.textContent = "Edit Akun";
            modalSubtitle.textContent = "Perbarui data pengguna, peran akses, kata sandi, atau status akun.";
            submitBtn.textContent = "Simpan Perubahan";

            emailInput.value = akun.email;
            usernameInput.value = akun.username;
            roleInput.value = akun.role;
            activeInput.checked = akun.isActive;

            // kata sandi tidak perlu diganti atau diisi ulang (masih tetap tersimpan)
            passwordInput.value = "";
            passwordInput.required = false;
            passwordInput.placeholder = "Kosongkan jika tidak ingin mengubah sandi";

            openModal();
        }

        // hapus akun
        if (deleteBtn) {
            const id = deleteBtn.dataset.id;
            const akun = daftarAkun.find((a) => a.id === id);
            if (!akun) return;

            if (deleteAkunModal && deleteModalText) {
                deletingAkunId = id;
                deleteModalText.innerHTML = `Apakah Anda yakin ingin menghapus akun <strong>${akun.username}</strong> (${akun.email})?`;
                deleteAkunModal.classList.add("is-open");
                deleteAkunModal.setAttribute("aria-hidden", "false");
            }
        }
    });

    // popup modal card konfirmasi hapus akun
    if (deleteAkunModal) {
        deleteAkunModal.querySelectorAll(".js-close-delete").forEach((btn) => {
            btn.addEventListener("click", closeDeleteModal);
        });

        deleteAkunModal.addEventListener("click", (e) => {
            if (e.target === deleteAkunModal) closeDeleteModal();
        });
    }

    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener("click", () => {
            if (deletingAkunId) {
                daftarAkun = daftarAkun.filter((a) => a.id !== deletingAkunId);
                renderAkunTable(daftarAkun);
            }
            closeDeleteModal();
        });
    }

    // render daftar tabel akun
    renderAkunTable(daftarAkun);
});