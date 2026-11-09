# Trio Saung Nusantara - Web Ordering System

Sistem pemesanan makanan dan manajemen transaksi berbasis **Web** untuk restoran **Trio Saung Nusantara**. Pelanggan dapat memesan makanan secara mandiri melalui pemindaian **QR Code** di meja saung, sementara Kasir dan Admin dapat mengelola pesanan dan transaksi secara terintegrasi.

---

## ✨ Fitur Utama

### 📱 1. Pelanggan (Customer)
* **Akses Tanpa Login**: Memindai QR Code untuk langsung masuk ke menu meja terkait.
* **Katalog & Filter**: Pencarian menu, filter kategori, dan melihat item rekomendasi.
* **Keranjang Belanja**: Menambah item (`+`), mengatur kuantitas, dan menambahkan catatan khusus (*notes*).
* **Checkout**: Menghitung subtotal & total otomatis, serta mengirimkan pesanan ke Kasir.
* **Call Staff**: Tombol panggil staf langsung dari meja.

### 💵 2. Kasir (Cashier)
* **Real-time Order**: Menerima notifikasi pesanan baru masuk dari meja secara instan.
* **Pengelolaan Stok**: Mengubah status ketersediaan menu (*Available* / *Out of Stock*).
* **Penggabungan Tagihan**: Mengakumulasi beberapa pesanan berstatus *Unpaid* dari meja yang sama.
* **Pembayaran**: Mencatat metode bayar (**Tunai**, **QRIS**, **Debit/Kredit**) & mencetak struk.

### ⚙️ 3. Admin
* **Manajemen Master Data**: CRUD Data Menu, Kategori, Meja, dan Akun Kasir.
* **QR Code Generator**: Membuat token QR Code khusus per meja.
* **Dashboard Laporan**: Memantau ringkasan transaksi & laporan penjualan.
