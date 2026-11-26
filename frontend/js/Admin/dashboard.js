document.addEventListener("DOMContentLoaded", async () => {
    const formatRupiah = (angka) =>
        "Rp " + new Intl.NumberFormat("id-ID").format(Number(angka || 0));

    const getInitials = (name) => {
        if (!name) return "AS";
        return name
            .trim()
            .split(/\s+/)
            .slice(0, 2)
            .map((part) => part[0].toUpperCase())
            .join("");
    };

    const renderProfile = (user) => {
        const avatarEl = document.getElementById("profileAvatar");
        const nameEl = document.getElementById("profileName");
        const emailEl = document.getElementById("profileEmail");
        const welcomeEl = document.getElementById("welcomeTitle");

        const displayName = user?.name || "Admin Saung";
        if (avatarEl) {
            avatarEl.textContent = getInitials(displayName);
            avatarEl.classList.add("has-initials");
        }
        if (nameEl) nameEl.textContent = displayName;
        if (emailEl) emailEl.textContent = user?.email || "admin@saung.com";
        if (welcomeEl) welcomeEl.textContent = `Selamat Datang, ${displayName.split(" ")[0]}!`;
    };

    const renderHourlyChart = (items) => {
        const chartEl = document.getElementById("hourlyChart");
        const peakTimeEl = document.getElementById("peakHourTime");
        if (!chartEl) return;

        // Jam operasional 10.00 - 21.00 WIB
        const hours = Array.from({ length: 12 }, (_, idx) => 10 + idx);
        const counts = Object.fromEntries(hours.map((h) => [h, 0]));

        (items || []).forEach((trx) => {
            if (!trx.paid_at) return;
            const dt = new Date(trx.paid_at);
            const hourWib = Number(
                new Intl.DateTimeFormat("en-GB", {
                    hour: "2-digit",
                    hour12: false,
                    timeZone: "Asia/Jakarta"
                }).format(dt)
            );
            if (counts[hourWib] !== undefined) {
                counts[hourWib] += 1;
            }
        });

        const maxCount = Math.max(...Object.values(counts), 0);
        let peakHour = null;
        if (maxCount > 0) {
            peakHour = hours.find((h) => counts[h] === maxCount);
        }

        if (peakTimeEl) {
            peakTimeEl.textContent =
                peakHour !== null
                    ? `${String(peakHour).padStart(2, "0")}.00-${String(peakHour + 1).padStart(2, "0")}.00`
                    : "Belum ada";
        }

        chartEl.innerHTML = "";
        hours.forEach((h) => {
            const count = counts[h];
            const heightPct = maxCount > 0 ? Math.max(8, Math.round((count / maxCount) * 100)) : 8;

            const col = document.createElement("div");
            col.className = "hour-col" + (h === peakHour ? " is-active" : "");
            col.innerHTML = `
                <span class="hour-value">${count}</span>
                <div class="hour-bar" style="height: ${heightPct}%"></div>
                <span class="hour-label">${String(h).padStart(2, "0")}.00</span>
            `;

            col.addEventListener("click", () => {
                chartEl.querySelectorAll(".hour-col").forEach((el) => el.classList.remove("is-active"));
                col.classList.add("is-active");
            });

            chartEl.appendChild(col);
        });
    };

    const renderTopMenus = (topMenus) => {
        const listEl = document.getElementById("topMenuList");
        if (!listEl) return;

        const top5 = (topMenus || []).slice(0, 5);
        if (top5.length === 0) {
            listEl.innerHTML = `<li class="dashboard-empty">Belum ada data penjualan menu hari ini.</li>`;
            return;
        }

        listEl.innerHTML = top5
            .map(
                (item, idx) => `
                <li class="top-menu-item">
                    <span class="rank-badge">${idx + 1}</span>
                    <span class="menu-name">${item.menu_name}</span>
                    <span class="menu-sold">${item.quantity_sold}x</span>
                </li>
            `
            )
            .join("");
    };

    const renderRecentTransactions = (items) => {
        const listEl = document.getElementById("recentTransactionsList");
        if (!listEl) return;

        const recent5 = (items || []).slice(0, 5);
        if (recent5.length === 0) {
            listEl.innerHTML = `<li class="dashboard-empty">Belum ada transaksi hari ini.</li>`;
            return;
        }

        listEl.innerHTML = recent5
            .map((trx) => {
                const jam = trx.paid_at
                    ? new Intl.DateTimeFormat("id-ID", {
                        hour: "2-digit",
                        minute: "2-digit",
                        timeZone: "Asia/Jakarta"
                    }).format(new Date(trx.paid_at))
                    : "-";
                const meja = trx.table_number ? `Meja ${trx.table_number}` : "Takeaway";
                const metode = (trx.payment_method || "").toUpperCase();

                return `
                    <li class="transaksi-item">
                        <div class="trx-left">
                            <span class="trx-code">${trx.receipt_number || "-"}</span>
                            <span class="trx-meta">${meja} • ${metode} • ${jam} WIB</span>
                        </div>
                        <span class="trx-amount">${formatRupiah(trx.total_amount)}</span>
                    </li>
                `;
            })
            .join("");
    };

    try {
        const [user, summary, trxData, menus] = await Promise.all([
            getCurrentUser(),
            getReportSummary(),
            getReportTransactions(100),
            getMenus()
        ]);

        localStorage.setItem("tsn_current_user", JSON.stringify(user));
        renderProfile(user);

        // 3 Kartu Ringkasan
        const totalPendapatanEl = document.getElementById("totalPendapatan");
        const totalPemesananEl = document.getElementById("totalPemesanan");
        const menuTersediaEl = document.getElementById("menuTersedia");

        if (totalPendapatanEl) totalPendapatanEl.textContent = formatRupiah(summary.revenue);
        if (totalPemesananEl) totalPemesananEl.textContent = summary.transactions ?? 0;

        if (menuTersediaEl && Array.isArray(menus)) {
            const availableCount = menus.filter((m) => m.is_available).length;
            menuTersediaEl.textContent = `${availableCount}/${menus.length}`;
        }

        renderHourlyChart(trxData.items);
        renderTopMenus(summary.top_menus);
        renderRecentTransactions(trxData.items);
    } catch (error) {
        console.error("Gagal memuat dashboard:", error);
        if (error.message?.toLowerCase().includes("login") || error.message?.toLowerCase().includes("token")) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("tsn_current_user");
            window.location.href = "/frontend/index.html";
        }
    }
});