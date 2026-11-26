document.addEventListener('DOMContentLoaded', () => {
    const detailTitle = document.getElementById('detail-title');
    const detailPrice = document.getElementById('detail-price');
    const detailDesc = document.getElementById('detail-desc');
    const detailImg = document.getElementById('detail-img');
    const carouselDots = document.getElementById('carousel-dots');
    const spicyGroup = document.getElementById('spicy-level-group');
    const spicyPills = document.querySelectorAll('.spicy-pill');
    const spicyHelper = document.getElementById('spicy-helper');
    const noteInput = document.getElementById('order-note');
    const qtyMinusBtn = document.getElementById('qty-minus');
    const qtyPlusBtn = document.getElementById('qty-plus');
    const qtyDisplay = document.getElementById('qty-display');
    const backBtn = document.getElementById('detail-back-btn');

    const addToCartBtn = document.getElementById('add-to-cart-btn');
    const btnSubtotalEl = document.getElementById('btn-subtotal');

    // ambil data menu terpilih dari sessionStorage / URL
    const params = new URLSearchParams(window.location.search);
    const menuIdFromUrl = params.get('id');
    const cachedMenu = JSON.parse(sessionStorage.getItem('tsn_selected_menu') || 'null');

    const currentMenu = cachedMenu || {
        id: menuIdFromUrl || 'nasi-goreng-kecombrang',
        name: 'Nasi Goreng Kecombrang',
        price: 45000,
        description: 'Dimasak dengan sambal kecombrang khas buatan Trio Saung Nusantara.',
        category: 'Makanan',
        hasSpicyLevel: true,
        images: []
    };

    // state keranjang dari localStorage
    let cart = JSON.parse(localStorage.getItem('tsn_cart')) || {};
    
    const menuId = String(currentMenu.id);
    const existingItem = cart[currentMenu.id];

    let currentQty = existingItem ? existingItem.qty : 1;
    let selectedLevel = existingItem?.spicyLevel || null;

    function formatRupiah(angka) {
        return 'Rp ' + Number(angka).toLocaleString('id-ID');
    }

    function returnToPreviousPage() {
        const savedReturnUrl = sessionStorage.getItem('tsn_return_url');

        if (savedReturnUrl && !savedReturnUrl.includes('detail.html')) {
            window.location.href = savedReturnUrl;
        } else if (document.referrer && !document.referrer.includes('detail.html')) {
            window.location.href = document.referrer;
        } else {
            window.location.href = 'main.html';
        }
    }

    //perbarui state stepper & tombol "Tambah ke Keranjang"
    function updateActionState() {
        const requiresSpicy = !spicyGroup.hidden;
        const isSpicyValid = !requiresSpicy || Boolean(selectedLevel);

        // nonaktifkan tombol plus, jika level pedas belum diisi
        qtyPlusBtn.disabled = !isSpicyValid;

        // qty = 1 (item baru), qty (0) = hapus (jika sudah ada di keranjang)
        const minQty = existingItem ? 0 : 1;
        qtyMinusBtn.disabled = !isSpicyValid || currentQty <= minQty;

        if (spicyHelper) {
            spicyHelper.hidden = isSpicyValid;
        }

        qtyDisplay.textContent = currentQty;

        // update label & status tombol konfirmasi bawah
        const btnLabelSpan = addToCartBtn.querySelector('span');
        if (!isSpicyValid) {
            addToCartBtn.disabled = true;
            btnLabelSpan.textContent = existingItem ? 'Perbarui Keranjang' : 'Tambah ke Keranjang';
            btnSubtotalEl.textContent = formatRupiah(currentQty * currentMenu.price);
        } else if (currentQty === 0 && existingItem) {
            addToCartBtn.disabled = false;
            btnLabelSpan.textContent = 'Hapus dari Keranjang';
            btnSubtotalEl.textContent = 'Rp 0';
        } else {
            addToCartBtn.disabled = false;
            btnLabelSpan.textContent = existingItem ? 'Perbarui Keranjang' : 'Tambah ke Keranjang';
            btnSubtotalEl.textContent = formatRupiah(currentQty * currentMenu.price);
        }
    }

    // render data menu ke tampilan
    function populateMenuDetail(menuData) {
        detailTitle.textContent = menuData.name;
        detailPrice.textContent = formatRupiah(menuData.price);
        detailDesc.textContent = menuData.description || '';

        const showSpicy = menuData.hasSpicyLevel !== undefined
            ? menuData.hasSpicyLevel
            : (menuData.category !== 'Minuman' && menuData.category !== 'Camilan');
        spicyGroup.hidden = !showSpicy;

        const imageList = Array.isArray(menuData.images)
            ? menuData.images
            : (menuData.image ? [menuData.image] : []);

        if (imageList.length > 0 && imageList[0]) {
            detailImg.src = imageList[0];
            detailImg.alt = menuData.name;
            detailImg.hidden = false;
        } else {
            detailImg.hidden = true;
        }

        if (carouselDots) {
            carouselDots.style.display = imageList.length > 1 ? 'flex' : 'none';
        }

        spicyPills.forEach(pill => {
            const isMatch = selectedLevel && pill.dataset.level === selectedLevel;
            pill.classList.toggle('active', Boolean(isMatch));
            pill.setAttribute('aria-checked', isMatch ? 'true' : 'false');
        });

        if (existingItem?.note) {
            noteInput.value = existingItem.note;
        }

        updateActionState();
    }

    // pilih Level Pedas
    spicyPills.forEach(pill => {
        pill.addEventListener('click', () => {
            spicyPills.forEach(p => {
                p.classList.remove('active');
                p.setAttribute('aria-checked', 'false');
            });
            pill.classList.add('active');
            pill.setAttribute('aria-checked', 'true');
            selectedLevel = pill.dataset.level;

            updateActionState();
        });
    });

    // stepper (+) dan (-)
    qtyPlusBtn.addEventListener('click', () => {
        currentQty += 1;
        updateActionState();
    });

    qtyMinusBtn.addEventListener('click', () => {
        const minQty = existingItem ? 0 : 1;
        if (currentQty > minQty) {
            currentQty -= 1;
            updateActionState();
        }
    });

    // klik "Tambah ke Keranjang" -> Simpan ke localStorage & kembali ke layar sebelumnya
    addToCartBtn.addEventListener('click', () => {
        if (addToCartBtn.disabled) return;

        if (currentQty <= 0) {
            delete cart[currentMenu.id];
        } else {
            cart[currentMenu.id] = {
                id: currentMenu.id,
                name: currentMenu.name,
                price: currentMenu.price,
                image: currentMenu.images?.[0] || currentMenu.image || '',
                qty: currentQty,
                spicyLevel: spicyGroup.hidden ? null : selectedLevel,
                note: noteInput.value.trim()
            };
        }

        localStorage.setItem('tsn_cart', JSON.stringify(cart));
        returnToPreviousPage();
    });

    addToCartBtn.addEventListener('pointerdown', () => {
        if (!addToCartBtn.disabled) addToCartBtn.classList.add('is-pressed');
    });
    const releasePress = () => setTimeout(() => addToCartBtn.classList.remove('is-pressed'), 160);
    addToCartBtn.addEventListener('pointerup', releasePress);
    addToCartBtn.addEventListener('pointercancel', releasePress);
    addToCartBtn.addEventListener('pointerleave', releasePress);

    // tombol arrow back
    if (backBtn) {
        backBtn.addEventListener('click', (e) => {
            e.preventDefault();
            returnToPreviousPage();
        });
    }

    populateMenuDetail(currentMenu);
});