document.addEventListener("DOMContentLoaded", () => {
    const PAGE_SIZE = 8;

    let activeDays = 7;
    let currentPage = 1;
    let allTransactions = [];
    let filteredTransactions = [];

    const rangeButtons = document.querySelectorAll(".range-btn");
    const exportCsvBtn = document.getElementById("exportCsvBtn");
    const searchInput = document.getElementById("trxSearch");
    const clearSearchBtn = document.getElementById("clearTrxSearch");
    const methodFilter = document.getElementById("methodFilter");
    const tableBody = document.getElementById("auditTableBody");
    const pageSummaryEl = document.getElementById("pageSummary");
    const pageControlsEl = document.getElementById("pageControls");

    // Elemen Modal Detail
    const detailModal = document.getElementById("trxDetailModal");
    const closeModalBtn = document.getElementById("closeTrxModalBtn");
    const closeModalFooter = document.getElementById("closeTrxModalFooter");

    const formatRupiah = (n) => "Rp " + new Intl.NumberFormat("id-ID").format(Number(n || 0));

    const toDateStrWIB = (dateObj) =>
        new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Jakarta" }).format(dateObj);

    const getDateRange = (days, offsetDays = 0) => {
        const end = new Date();
        end.setDate(end.getDate() - offsetDays);
        const start = new Date(end);
        start.setDate(end.getDate() - (days - 1));
        return { from: toDateStrWIB(start), to: toDateStrWIB(end) };
    };

    const formatDateTime = (iso) => {
        if (!iso) return "-";
        const dt = new Date(iso);
        const tgl = new Intl.DateTimeFormat("id-ID", {
            day: "2-digit",
            month: "2-digit",
            year: "numeric",
            timeZone: "Asia/Jakarta"
        }).format(dt);
        const jam = new Intl.DateTimeFormat("id-ID", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
            timeZone: "Asia/Jakarta"
        })
            .format(dt)
            .replace(":", ".");
        return `${tgl} • ${jam}`;
    };

    const formatMethodLabel = (method) => {
        const key = (method || "").toLowerCase();
        if (key === "qris") return "QRIS";
        if (key === "debit" || key === "card" || key === "cc") return "Debit / CC";
        if (key === "cash" || key === "tunai") return "Tunai";
        return method ? method.toUpperCase() : "-";
    };

    const renderProfile = (user) => {
        const avatarEl = document.getElementById("profileAvatar");
        const nameEl = document.getElementById("profileName");
        const emailEl = document.getElementById("profileEmail");
        const displayName = user?.name || "Admin Saung";

        if (avatarEl) {
            avatarEl.textContent = displayName
                .trim()
                .split(/\s+/)
                .slice(0, 2)
                .map((p) => p[0].toUpperCase())
                .join("");
            avatarEl.classList.add("has-initials");
        }
        if (nameEl) nameEl.textContent = displayName;
        if (emailEl) emailEl.textContent = user?.email || "admin@saung.com";
    };

    const setTrendText = (elId, diff, suffix, isPercent = false, prevValue = 0) => {
        const el = document.getElementById(elId);
        if (!el) return;
        el.classList.remove("is-up", "is-down");

        if (isPercent) {
            const pct = prevValue > 0 ? Math.round((diff / prevValue) * 100) : diff > 0 ? 100 : 0;
            const arrow = pct >= 0 ? "▲" : "▼";
            el.classList.add(pct >= 0 ? "is-up" : "is-down");
            el.textContent = `${arrow} ${Math.abs(pct)}% ${suffix}`;
            return;
        }

        const arrow = diff >= 0 ? "▲" : "▼";
        el.classList.add(diff >= 0 ? "is-up" : "is-down");
        el.textContent = `${arrow} ${Math.abs(diff)} ${suffix}`;
    };

    const sumSoldItems = (summary) =>
        (summary?.top_menus || []).reduce((acc, m) => acc + Number(m.quantity_sold || 0), 0);

    // search bar + metode bayar
    const applyFilters = () => {
        const q = (searchInput?.value || "").trim().toLowerCase();
        const method = (methodFilter?.value || "").toLowerCase();

        filteredTransactions = allTransactions.filter((trx) => {
            const code = (trx.receipt_number || "").toLowerCase();
            const formattedTime = formatDateTime(trx.paid_at).toLowerCase();
            const matchSearch = !q || code.includes(q) || formattedTime.includes(q);

            const trxMethod = (trx.payment_method || "").toLowerCase();
            const matchMethod =
                !method ||
                trxMethod === method ||
                (method === "debit" && (trxMethod === "card" || trxMethod === "cc")) ||
                (method === "cash" && trxMethod === "tunai");

            return matchSearch && matchMethod;
        });

        currentPage = 1;
        renderTable();
    };

    const renderTable = () => {
        if (!tableBody) return;

        const totalItems = filteredTransactions.length;
        const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
        if (currentPage > totalPages) currentPage = totalPages;

        const startIdx = (currentPage - 1) * PAGE_SIZE;
        const pageRows = filteredTransactions.slice(startIdx, startIdx + PAGE_SIZE);

        if (pageRows.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="8" class="audit-empty-row">
                        Belum ada data transaksi pada rentang atau filter yang dipilih.
                    </td>
                </tr>
            `;
        } else {
            tableBody.innerHTML = pageRows
                .map((trx, idx) => {
                    const globalIdx = startIdx + idx;
                    const meja = trx.table_number ? `Meja ${String(trx.table_number).padStart(2, "0")}` : "Takeaway";
                    const porsi = trx.total_items ? `${trx.total_items} Porsi` : "-";

                    return `
                        <tr>
                            <td>${formatDateTime(trx.paid_at)}</td>
                            <td>${trx.receipt_number || "-"}</td>
                            <td>${meja}</td>
                            <td>${porsi}</td>
                            <td>${formatRupiah(trx.total_amount)}</td>
                            <td>${formatMethodLabel(trx.payment_method)}</td>
                            <td><span class="status-lunas">Lunas</span></td>
                            <td>
                                <button type="button" class="btn-detail" data-index="${globalIdx}">Detail</button>
                            </td>
                        </tr>
                    `;
                })
                .join("");
        }

        renderPagination(totalPages);
    };

    const renderPagination = (totalPages) => {
        if (pageSummaryEl) {
            pageSummaryEl.textContent = `Halaman ${currentPage} dari ${totalPages}`;
        }
        if (!pageControlsEl) return;

        let html = `<button type="button" class="page-nav-btn" data-page="${currentPage - 1}" ${
            currentPage === 1 ? "disabled" : ""
        }>&lt; Prev</button>`;

        for (let p = 1; p <= totalPages; p++) {
            const show = p === 1 || p === totalPages || Math.abs(p - currentPage) <= 1;
            if (show) {
                html += `<button type="button" class="page-btn ${
                    p === currentPage ? "is-active" : ""
                }" data-page="${p}">${p}</button>`;
            } else if (p === 2 && currentPage > 3) {
                html += `<span class="page-ellipsis">...</span>`;
            } else if (p === totalPages - 1 && currentPage < totalPages - 2) {
                html += `<span class="page-ellipsis">...</span>`;
            }
        }

        html += `<button type="button" class="page-nav-btn" data-page="${currentPage + 1}" ${
            currentPage === totalPages ? "disabled" : ""
        }>Next &gt;</button>`;

        pageControlsEl.innerHTML = html;
    };

    // Modal Detail Transaksi
    const openDetailModal = (trx) => {
        if (!detailModal || !trx) return;

        document.getElementById("trxModalCode").textContent = trx.receipt_number || "-";
        document.getElementById("trxModalTotal").textContent = formatRupiah(trx.total_amount);

        const meja = trx.table_number ? `Meja ${String(trx.table_number).padStart(2, "0")}` : "Takeaway";
        document.getElementById("trxDetailMeta").innerHTML = `
            <div><span>Tanggal/Jam</span><strong>${formatDateTime(trx.paid_at)}</strong></div>
            <div><span>Meja</span><strong>${meja}</strong></div>
            <div><span>Metode Bayar</span><strong>${formatMethodLabel(trx.payment_method)}</strong></div>
            <div><span>Kasir</span><strong>${trx.cashier_name || "-"}</strong></div>
        `;

        const itemsList = document.getElementById("trxDetailItems");
        if (Array.isArray(trx.items) && trx.items.length > 0) {
            itemsList.innerHTML = trx.items
                .map(
                    (it) => `
                    <li>
                        <span>${it.menu_name} (${it.quantity}x)</span>
                        <strong>${formatRupiah(it.subtotal || it.unit_price * it.quantity)}</strong>
                    </li>
                `
                )
                .join("");
        } else {
            itemsList.innerHTML = `<li><span>Total Porsi</span><strong>${
                trx.total_items ? `${trx.total_items} Porsi` : "Lunas"
            }</strong></li>`;
        }

        detailModal.classList.add("is-open");
        detailModal.setAttribute("aria-hidden", "false");
    };

    const closeDetailModal = () => {
        if (!detailModal) return;
        detailModal.classList.remove("is-open");
        detailModal.setAttribute("aria-hidden", "true");
    };

    // Fetch data berdasarkan filter 7 Hari / 30 Hari
    const loadReportData = async (days) => {
        const currentRange = getDateRange(days, 0);
        const prevRange = getDateRange(days, days);
        const periodLabel = days === 7 ? "minggu ini" : "30 hari ini";

        try {
            const [currSummary, prevSummary, trxData] = await Promise.all([
                getReportSummaryByRange(currentRange.from, currentRange.to),
                getReportSummaryByRange(prevRange.from, prevRange.to),
                getReportTransactionsByRange(currentRange.from, currentRange.to, 100, 0)
            ]);

            const currRevenue = Number(currSummary.revenue || 0);
            const prevRevenue = Number(prevSummary.revenue || 0);
            const currOrders = Number(currSummary.transactions || 0);
            const prevOrders = Number(prevSummary.transactions || 0);
            const currItems = sumSoldItems(currSummary);
            const prevItems = sumSoldItems(prevSummary);

            document.getElementById("cardRevenue").textContent = formatRupiah(currRevenue);
            document.getElementById("cardOrders").textContent = currOrders;
            document.getElementById("cardItems").textContent = `${currItems} porsi`;

            setTrendText("trendRevenue", currRevenue - prevRevenue, periodLabel, true, prevRevenue);
            setTrendText("trendOrders", currOrders - prevOrders, "pesanan");
            setTrendText("trendItems", currItems - prevItems, "porsi");

            allTransactions = trxData.items || [];
            applyFilters();
        } catch (err) {
            console.error("Gagal memuat laporan:", err);
        }
    };

    // Ekspor CSV dari data yang sedang tampil
    const exportCsv = () => {
        if (filteredTransactions.length === 0) return;

        const headers = ["Tanggal/Jam", "No. Transaksi", "Meja", "Total Item", "Total", "Metode", "Status"];
        const rows = filteredTransactions.map((trx) => [
            `"${formatDateTime(trx.paid_at)}"`,
            `"${trx.receipt_number || "-"}"`,
            `"${trx.table_number ? `Meja ${trx.table_number}` : "Takeaway"}"`,
            `"${trx.total_items || 0} Porsi"`,
            trx.total_amount || 0,
            `"${formatMethodLabel(trx.payment_method)}"`,
            `"Lunas"`
        ]);

        const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const url = URL.createObjectURL(blob);

        const link = document.createElement("a");
        link.href = url;
        link.download = `laporan-transaksi-${activeDays}-hari.csv`;
        link.click();
        URL.revokeObjectURL(url);
    };

    // Event Listeners
    rangeButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            rangeButtons.forEach((b) => b.classList.remove("is-active"));
            btn.classList.add("is-active");
            activeDays = Number(btn.dataset.days);
            loadReportData(activeDays);
        });
    });

    if (searchInput && clearSearchBtn) {
        searchInput.addEventListener("input", () => {
            clearSearchBtn.hidden = searchInput.value.length === 0;
            applyFilters();
        });
        clearSearchBtn.addEventListener("click", () => {
            searchInput.value = "";
            clearSearchBtn.hidden = true;
            applyFilters();
        });
    }

    if (methodFilter) methodFilter.addEventListener("change", applyFilters);
    if (exportCsvBtn) exportCsvBtn.addEventListener("click", exportCsv);

    if (pageControlsEl) {
        pageControlsEl.addEventListener("click", (e) => {
            const btn = e.target.closest("button[data-page]");
            if (!btn || btn.disabled) return;
            currentPage = Number(btn.dataset.page);
            renderTable();
        });
    }

    if (tableBody) {
        tableBody.addEventListener("click", (e) => {
            const btn = e.target.closest(".btn-detail");
            if (!btn) return;
            const trx = filteredTransactions[Number(btn.dataset.index)];
            openDetailModal(trx);
        });
    }

    if (closeModalBtn) closeModalBtn.addEventListener("click", closeDetailModal);
    if (closeModalFooter) closeModalFooter.addEventListener("click", closeDetailModal);
    if (detailModal) {
        detailModal.addEventListener("click", (e) => {
            if (e.target === detailModal) closeDetailModal();
        });
    }

    // Inisialisasi awal: load profil & data 7 hari
    (async () => {
        try {
            const user = await getCurrentUser();
            localStorage.setItem("tsn_current_user", JSON.stringify(user));
            renderProfile(user);
        } catch (err) {
            localStorage.removeItem("access_token");
            localStorage.removeItem("tsn_current_user");
            window.location.href = "/frontend/index.html";
            return;
        }
        await loadReportData(activeDays);
    })();
});