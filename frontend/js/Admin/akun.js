document.addEventListener("DOMContentLoaded", () => {
    // state daftar akun yang terdaftar di database
    let daftarAkun = [];

    // elemen profil kartu akun di sidebar kiri
    const profileTitleEl = document.querySelector(".acc-card h3");
    const profileEmailEl = document.querySelector(".acc-card p");

    // elemen badan tabel akun
    const akunTableBody = document.getElementById("isi-tabel-akun");
    if (!akunTableBody) return;

    // sinkronkan nama dan email pada kartu profil sidebar sesuai role login
    function syncSidebarProfile() {
        const storedUser = JSON.parse(
            localStorage.getItem("tsn_current_user") ||
            sessionStorage.getItem("tsn_current_user") ||
            "null"
        );

        const activeRole = (storedUser?.role || "admin").toLowerCase();
        const activeEmail = storedUser?.email || (activeRole === "kasir" ? "kasir@saung.com" : "admin@saung.com");

        if (profileTitleEl) {
            profileTitleEl.textContent = activeRole === "kasir" ? "Kasir Saung" : "Admin Saung";
        }
        if (profileEmailEl) {
            profileEmailEl.textContent = activeEmail;
        }
    }

    // render baris tabel daftar akun (3 kolom: email, peran, status)
    function renderAkunTable(data) {
        akunTableBody.innerHTML = "";

        if (!data || data.length === 0) {
            akunTableBody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state">
                        Belum ada akun pengguna yang terdaftar di database.
                    </td>
                </tr>
            `;
            return;
        }

        data.forEach((akun) => {
            const roleKey = (akun.role || "kasir").toLowerCase();
            const roleLabel = roleKey.charAt(0).toUpperCase() + roleKey.slice(1);

            const statusHTML = akun.isActive
                ? `<div class="tersedia">Aktif</div>`
                : `<div class="tak-tersedia">Nonaktif</div>`;

            const row = `
                <tr class="baris-menu" data-id="${akun.id}">
                    <td>${akun.email}</td>
                    <td><span class="badge-role role-${roleKey}">${roleLabel}</span></td>
                    <td>
                        <div class="ketersediaan">${statusHTML}</div>
                    </td>
                </tr>
            `;

            akunTableBody.insertAdjacentHTML("beforeend", row);
        });
    }

    // inisialisasi tampilan awal
    syncSidebarProfile();
    renderAkunTable(daftarAkun);
});