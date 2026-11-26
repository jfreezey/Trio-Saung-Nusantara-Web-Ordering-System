document.addEventListener('DOMContentLoaded', () => {
    const cartListEl = document.getElementById('cart-items-list');
    const summaryCardEl = document.getElementById('ringkasan');
    const checkoutDockEl = document.getElementById('checkout-dock');
    const subtotalEl = document.getElementById('summary-subtotal');
    const taxEl = document.getElementById('summary-tax');
    const grandTotalEl = document.getElementById('summary-grand-total');
    const checkoutBtn = document.getElementById('checkout-btn');
    const checkoutOverlay = document.getElementById('checkout-overlay');
    const successScreen = document.getElementById('order-success-screen');
    const successTableBadge = document.getElementById('success-table-badge');
    const backBtn = document.getElementById('cart-back-btn');

    const TAX_RATE = 0.12; // Pajak restoran 12%
    let cart = JSON.parse(localStorage.getItem('tsn_cart')) || {};
    let expandedItemId = null;

    function formatRupiah(angka) {
        return 'Rp ' + Math.round(Number(angka)).toLocaleString('id-ID');
    }

    // 1. Tampilkan Nomor Meja di Topbar
    function initTableBadge() {
        const tableBadge = document.getElementById('table-badge');
        if (!tableBadge) return;

        const activeTable = sessionStorage.getItem('tsn_table_number') || '05';
        const formattedNumber = /^\d+$/.test(activeTable)
            ? activeTable.padStart(2, '0')
            : activeTable.toUpperCase();

        tableBadge.textContent = `Meja • ${formattedNumber}`;
        tableBadge.dataset.table = formattedNumber;
    }

    // 2. Hitung & Render Subtotal, Pajak 12%, dan Total Akhir
    function updateTotals() {
        const items = Object.values(cart);
        const subtotal = items.reduce((sum, item) => sum + (item.price * item.qty), 0);
        const tax = Math.round(subtotal * TAX_RATE);
        const grandTotal = subtotal + tax;

        subtotalEl.textContent = formatRupiah(subtotal);
        taxEl.textContent = formatRupiah(tax);
        grandTotalEl.textContent = formatRupiah(grandTotal);
    }

    // 3. Render Daftar Item di Keranjang
    function renderCartItems() {
        localStorage.setItem('tsn_cart', JSON.stringify(cart));
        const items = Object.values(cart);

        if (items.length === 0) {
            cartListEl.innerHTML = `
                <div class="empty-cart-box">
                    <p>Keranjang pesananmu masih kosong.</p>
                    <a href="main.html" class="empty-cart-link">Lihat Daftar Menu</a>
                </div>
            `;
            summaryCardEl.style.display = 'none';
            checkoutDockEl.style.display = 'none';
            return;
        }

        summaryCardEl.style.display = 'flex';
        checkoutDockEl.style.display = 'flex';

        cartListEl.innerHTML = items.map(item => {
            const isExpanded = expandedItemId === item.id;
            const stateClass = isExpanded ? 'is-expanded' : 'is-collapsed';
            const itemSubtotal = item.price * item.qty;

            return `
                <article class="cart-item-row" data-id="${item.id}">
                    <div class="cart-item-thumb">
                        ${item.image ? `<img src="${item.image}" alt="${item.name}">` : ''}
                    </div>
                    <div class="cart-item-details">
                        <div class="cart-item-top">
                            <h2 class="cart-item-title">${item.name}</h2>
                            <span class="cart-item-price">${formatRupiah(itemSubtotal)}</span>
                        </div>
                        ${item.spicyLevel ? `<p class="cart-item-spicy">${item.spicyLevel}</p>` : ''}
                        ${item.note ? `<p class="cart-item-note">${item.note}</p>` : ''}
                        <div class="cart-item-bottom">
                            <button type="button" class="cart-edit-btn" data-id="${item.id}">Edit</button>
                            <div class="qty-stepper ${stateClass}" data-id="${item.id}">
                                <button type="button" class="step-btn step-minus" aria-label="Kurangi jumlah">
                                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"/></svg>
                                </button>
                                <span class="step-count">${item.qty}</span>
                                <button type="button" class="step-btn step-plus" aria-label="Tambah jumlah">
                                    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
                                </button>
                            </div>
                        </div>
                    </div>
                </article>
            `;
        }).join('');

        updateTotals();
    }

    function collapseAllSteppers() {
        if (!expandedItemId) return;
        expandedItemId = null;
        document.querySelectorAll('.qty-stepper.is-expanded').forEach(stepper => {
            stepper.classList.remove('is-expanded');
            stepper.classList.add('is-collapsed');
        });
    }

    // 4. Interaksi Tombol Edit & Stepper Kuantitas di Keranjang
    cartListEl.addEventListener('click', (e) => {
        // Klik tombol Edit -> buka detail.html untuk ubah level pedas/catatan/jumlah
        const editBtn = e.target.closest('.cart-edit-btn');
        if (editBtn) {
            const id = editBtn.dataset.id;
            const item = cart[id];
            if (!item) return;

            sessionStorage.setItem('tsn_return_url', window.location.href);
            sessionStorage.setItem('tsn_selected_menu', JSON.stringify({
                id: item.id,
                name: item.name,
                price: item.price,
                description: item.description || '',
                hasSpicyLevel: Boolean(item.spicyLevel),
                images: item.image ? [item.image] : []
            }));

            window.location.href = `detail.html?id=${encodeURIComponent(id)}`;
            return;
        }

        // Klik Stepper (+ / - / badge angka)
        const stepper = e.target.closest('.qty-stepper');
        if (!stepper) return;

        const id = stepper.dataset.id;
        if (!cart[id]) return;

        if (stepper.classList.contains('is-collapsed')) {
            expandedItemId = id;
            renderCartItems();
            return;
        }

        if (e.target.closest('.step-plus')) {
            cart[id].qty += 1;
            expandedItemId = id;
            renderCartItems();
            return;
        }

        if (e.target.closest('.step-minus')) {
            cart[id].qty -= 1;
            if (cart[id].qty <= 0) {
                delete cart[id];
                expandedItemId = null;
            } else {
                expandedItemId = id;
            }
            renderCartItems();
        }
    });

    window.addEventListener('scroll', collapseAllSteppers, { passive: true });
    document.addEventListener('pointerdown', (e) => {
        if (expandedItemId && !e.target.closest('.qty-stepper')) {
            collapseAllSteppers();
        }
    });

    // 5. Tombol Checkout Pesanan -> Popup Loading -> Layar Checklist Pesanan Diterima
    checkoutBtn.addEventListener('click', () => {
        const items = Object.values(cart);
        if (items.length === 0 || checkoutBtn.disabled) return;

        // Tahap 1: Ubah tombol menjadi state loading smooth
        checkoutBtn.disabled = true;
        checkoutBtn.classList.add('is-loading');
        checkoutBtn.querySelector('.btn-text').textContent = 'Memproses Pesanan...';

        // Format nomor meja aktif
        const activeTable = sessionStorage.getItem('tsn_table_number') || '05';
        const formattedTable = /^\d+$/.test(activeTable)
            ? activeTable.padStart(2, '0')
            : activeTable.toUpperCase();

        // Siapkan payload pesanan (siap dikirim ke Firestore / Kasir)
        const subtotal = items.reduce((sum, item) => sum + (item.price * item.qty), 0);
        const tax = Math.round(subtotal * TAX_RATE);
        const orderPayload = {
            tableNumber: formattedTable,
            items,
            subtotal,
            tax,
            total: subtotal + tax,
            status: 'cooking',
            createdAt: new Date().toISOString()
        };
        sessionStorage.setItem('tsn_last_order', JSON.stringify(orderPayload));

        // Tahap 2: Tampilkan popup loading (.checkout-popup-dialog)
        setTimeout(() => {
            checkoutOverlay.classList.add('is-visible');
            checkoutOverlay.setAttribute('aria-hidden', 'false');
        }, 250);

        // Tahap 3: Tutup popup loading & munculkan layar penuh Pesanan Diterima + animasi checklist
        setTimeout(() => {
            localStorage.removeItem('tsn_cart'); // Kosongkan keranjang

            if (successTableBadge) {
                successTableBadge.textContent = `Meja • ${formattedTable}`;
            }

            checkoutOverlay.classList.remove('is-visible');
            checkoutOverlay.setAttribute('aria-hidden', 'true');

            if (successScreen) {
                successScreen.classList.add('is-active');
                successScreen.setAttribute('aria-hidden', 'false');
            }
        }, 1450);
    });

    // Tombol Kembali ke Halaman Katalog
    if (backBtn) {
        backBtn.addEventListener('click', (e) => {
            e.preventDefault();
            if (document.referrer && !document.referrer.includes('cart.html') && !document.referrer.includes('detail.html')) {
                window.location.href = document.referrer;
            } else {
                window.location.href = 'main.html';
            }
        });
    }

    initTableBadge();
    renderCartItems();
});

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.location.reload();
    }
});