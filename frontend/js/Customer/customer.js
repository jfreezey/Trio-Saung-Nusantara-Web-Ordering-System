// format angka ke Rupiah 
function formatRupiah(angka) {
    return 'Rp ' + Number(angka).toLocaleString('id-ID');
}

// stepper expand
function createStepperHTML(id, qty, isExpanded = false) {
    const stateClass = qty <= 0 
        ? 'is-empty' 
        : (isExpanded ? 'is-expanded' : 'is-collapsed');

    return `
        <div class="qty-stepper ${stateClass}" data-id="${id}">
            <button type="button" class="step-btn step-minus" aria-label="Kurangi jumlah">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14"/></svg>
            </button>
            <span class="step-count">${qty}</span>
            <button type="button" class="step-btn step-plus" aria-label="Tambah jumlah">
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            </button>
        </div>
    `;
}

// render kartu menu dari array data 
function renderMenus(menus, cart = {}) {
    const menuListContainer = document.getElementById('menu-list');
    if (!menuListContainer) return;

    if (!menus || menus.length === 0) {
        menuListContainer.innerHTML = `<p class="empty-menu">Belum ada menu yang tersedia.</p>`;
        return;
    }

    menuListContainer.innerHTML = menus.map(item => {
        const qty = cart[item.id] ? cart[item.id].qty : 0;
        const hasSpicyLevel = Boolean(item.hasSpicyLevel);

        return `
            <article class="menu-card" data-id="${item.id}" data-has-spicy="${hasSpicyLevel}">
                <div class="food-image">
                    ${item.image ? `<img src="${item.image}" alt="${item.name}" loading="lazy">` : ''}
                </div>
                <div class="food-info">
                    <h3>${item.name}</h3>
                    <p>${item.description || ''}</p>
                    <div class="food-footer">
                        <strong>${formatRupiah(item.price)}</strong>
                        ${createStepperHTML(item.id, qty, false)}
                    </div>
                </div>
            </article>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.querySelector('.search-bar');
    const clearBtn = document.querySelector('.search .clear');
    const menuGrid = document.querySelector('.menu-grid');
    const cartSummary = document.querySelector('.cart-summary');
    const cartCountEl = document.querySelector('.cart-count');
    const cartTotalEl = cartSummary ? cartSummary.querySelector('strong') : null;
    const cartDock = document.getElementById('cart-dock');

    let expandedCardId = null;
    let cart = JSON.parse(localStorage.getItem('tsn_cart')) || {};

    // cek lagi jalan di tampilan mana
    const activeCategory = document.body.dataset.category || '';

    let defaultDisplayMenus = []; 
    // tampilan menu yg dicari
    let searchableMenus = [];    

    function parseHarga(hargaText) {
        return parseInt(hargaText.replace(/[^\d]/g, ''), 10) || 0;
    }

    // sumber data
    function initMenuDataSource() {
        const globalMenus = Array.isArray(window.TSN_ALL_MENUS) ? window.TSN_ALL_MENUS : [];

        if (globalMenus.length > 0) {
            if (activeCategory) {
                // halaman kategori
                const categoryItems = globalMenus.filter(
                    item => item.category.toLowerCase() === activeCategory.toLowerCase()
                );
                defaultDisplayMenus = categoryItems;
                searchableMenus = categoryItems;
            } else {
                // halaman utama (search semua)
                const recommended = globalMenus.filter(item => item.isRecommended);
                defaultDisplayMenus = recommended.length > 0 ? recommended : globalMenus;
                searchableMenus = globalMenus;
            }

            renderMenus(defaultDisplayMenus, cart);
            return;
        }

        const cards = document.querySelectorAll('#menu-list .menu-card');
        const domMenus = Array.from(cards).map((card, index) => {
            const name = card.querySelector('h3')?.textContent.trim() || `Menu ${index + 1}`;
            const id = card.dataset.id || name.toLowerCase().replace(/\s+/g, '-');
            card.dataset.id = id;

            return {
                id,
                name,
                description: card.querySelector('p')?.textContent.trim() || '',
                price: parseHarga(card.querySelector('strong')?.textContent || '0'),
                image: card.querySelector('.food-image img')?.getAttribute('src') || '',
                hasSpicyLevel: card.dataset.hasSpicy === 'true',
                category: card.dataset.category || activeCategory
            };
        });

        defaultDisplayMenus = domMenus;
        searchableMenus = domMenus;
    }

    // filter pencarian
    function handleSearchFilter(rawKeyword) {
        const keyword = rawKeyword.trim().toLowerCase();
        const isSearching = keyword.length > 0;

        document.body.classList.toggle('is-searching', isSearching);

        if (clearBtn) {
            clearBtn.hidden = !isSearching;
        }

        collapseAllSteppers();

        const menuListContainer = document.getElementById('menu-list');
        if (!menuListContainer) return;

        // jika search kosong, kembali ke tampilan awal 
        if (!isSearching) {
            renderMenus(defaultDisplayMenus, cart);
            syncCardsWithCart();
            return;
        }

        // search semua menu dari semua kategori di main
        const filteredMenus = searchableMenus.filter(item =>
            item.name.toLowerCase().includes(keyword) ||
            (item.description && item.description.toLowerCase().includes(keyword)) ||
            (item.category && item.category.toLowerCase().includes(keyword))
        );

        if (filteredMenus.length === 0) {
            menuListContainer.innerHTML = `
                <div class="empty-search-state">
                    <strong>Menu tidak ditemukan</strong>
                    Tidak ada hidangan yang cocok dengan kata kunci "${rawKeyword.trim()}".
                </div>
            `;
            return;
        }

        renderMenus(filteredMenus, cart);
        syncCardsWithCart();
    }

    if (searchInput) {
        searchInput.addEventListener('input', () => {
            handleSearchFilter(searchInput.value);
        });

        searchInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchInput.blur();
            }
        });
    }

    if (clearBtn && searchInput) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            handleSearchFilter('');
            searchInput.focus();
        });
    }

    // badge meja
    function initTableBadge() {
        const tableBadge = document.getElementById('table-badge');
        if (!tableBadge) return;

        const params = new URLSearchParams(window.location.search);
        const scannedTable = params.get('meja') || params.get('table');

        if (scannedTable) {
            sessionStorage.setItem('tsn_table_number', scannedTable.trim());
        }

        const activeTable = sessionStorage.getItem('tsn_table_number') || '05';
        const formattedNumber = /^\d+$/.test(activeTable)
            ? activeTable.padStart(2, '0')
            : activeTable.toUpperCase();

        tableBadge.textContent = `Meja • ${formattedNumber}`;
        tableBadge.dataset.table = formattedNumber;
    }

    // tombol keranjang
    function updateCartUI() {
        localStorage.setItem('tsn_cart', JSON.stringify(cart));

        let totalItems = 0;
        let totalPrice = 0;

        Object.values(cart).forEach(item => {
            totalItems += item.qty;
            totalPrice += item.qty * item.price;
        });

        if (cartDock && cartCountEl && cartTotalEl) {
            if (totalItems > 0) {
                cartDock.style.display = 'flex';
                cartCountEl.innerHTML = `•&nbsp; ${totalItems} item`;
                cartTotalEl.textContent = formatRupiah(totalPrice);
                cartSummary.setAttribute('aria-label', `Keranjang, ${totalItems} item, total ${formatRupiah(totalPrice)}`);
            } else {
                cartDock.style.display = 'none';
            }
        }
    }

    // stepper dan logika navigasi
    function collapseAllSteppers() {
        if (!expandedCardId) return;
        expandedCardId = null;
        document.querySelectorAll('.qty-stepper.is-expanded').forEach(stepper => {
            stepper.classList.remove('is-expanded');
            stepper.classList.add('is-collapsed');
        });
    }

    // mengarah ke detail menu jika menu ada level kepedasannya
    function goToMenuDetail(card) {
        const name = card.querySelector('h3')?.textContent.trim() || '';
        const id = card.dataset.id || name.toLowerCase().replace(/\s+/g, '-');
        const description = card.querySelector('p')?.textContent.trim() || '';
        const price = parseHarga(card.querySelector('strong')?.textContent || '0');
        const imgSrc = card.querySelector('.food-image img')?.getAttribute('src') || '';
        const pageCategory = document.body.dataset.category || 'Makanan';
        const hasSpicyLevel = card.dataset.hasSpicy === 'true'; 

        sessionStorage.setItem('tsn_return_url', window.location.href);
        sessionStorage.setItem('tsn_selected_menu', JSON.stringify({
            id,
            name,
            description,
            price,
            category: pageCategory,
            hasSpicyLevel,
            images: imgSrc ? [imgSrc] : []
        }));

        window.location.href = `detail.html?id=${encodeURIComponent(id)}`;
    }

    function syncCardsWithCart() {
        document.querySelectorAll('.menu-card').forEach((card, index) => {
            const name = card.querySelector('h3')?.textContent.trim() || `Menu ${index}`;
            const id = card.dataset.id || name.toLowerCase().replace(/\s+/g, '-');
            card.dataset.id = id;

            const qty = cart[id]?.qty || 0;
            const isExpanded = (qty > 0 && expandedCardId === id);

            const existingControl = card.querySelector('.qty-stepper, .btn-qty, .add, .quantity');
            if (existingControl) {
                existingControl.outerHTML = createStepperHTML(id, qty, isExpanded);
            }
        });
    }

    if (menuGrid) {
        menuGrid.addEventListener('click', (e) => {
            const stepper = e.target.closest('.qty-stepper');

            if (stepper) {
                e.stopPropagation();
                const card = stepper.closest('.menu-card');
                const id = card.dataset.id;
                const name = card.querySelector('h3').textContent.trim();
                const price = parseHarga(card.querySelector('strong').textContent);
                const imgSrc = card.querySelector('.food-image img')?.getAttribute('src') || '';
                const hasSpicyLevel = card.dataset.hasSpicy === 'true';

                if (hasSpicyLevel) {
                    collapseAllSteppers();
                    goToMenuDetail(card);
                    return;
                }

                if (stepper.classList.contains('is-collapsed')) {
                    collapseAllSteppers();
                    expandedCardId = id;
                    syncCardsWithCart();
                    return;
                }

                if (e.target.closest('.step-plus')) {
                    if (expandedCardId && expandedCardId !== id) {
                        collapseAllSteppers();
                    }

                    if (!cart[id]) {
                        cart[id] = { id, name, price, image: imgSrc, qty: 1, spicyLevel: null };
                    } else {
                        cart[id].qty += 1;
                    }

                    expandedCardId = id;
                    syncCardsWithCart();
                    updateCartUI();
                    return;
                }

                if (e.target.closest('.step-minus')) {
                    if (cart[id]) {
                        cart[id].qty -= 1;
                        if (cart[id].qty <= 0) {
                            delete cart[id];
                            expandedCardId = null;
                        } else {
                            expandedCardId = id;
                        }
                        syncCardsWithCart();
                        updateCartUI();
                    }
                    return;
                }
                return;
            }

            collapseAllSteppers();
            const card = e.target.closest('.menu-card');
            if (card) {
                goToMenuDetail(card);
            }
        });
    }

    window.addEventListener('scroll', collapseAllSteppers, { passive: true });
    window.addEventListener('touchmove', collapseAllSteppers, { passive: true });

    document.addEventListener('pointerdown', (e) => {
        if (expandedCardId && !e.target.closest('.qty-stepper')) {
            collapseAllSteppers();
        }
    });

    if (cartSummary) {
        cartSummary.addEventListener('pointerdown', () => {
            cartSummary.classList.add('is-pressed');
        });

        const releasePress = () => {
            setTimeout(() => {
                cartSummary.classList.remove('is-pressed');
            }, 160);
        };

        cartSummary.addEventListener('pointerup', releasePress);
        cartSummary.addEventListener('pointercancel', releasePress);
        cartSummary.addEventListener('pointerleave', releasePress);
    }

    // urutan eksekusi
    initMenuDataSource();
    initTableBadge();
    syncCardsWithCart();
    updateCartUI();
});

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        window.location.reload();
    }
});