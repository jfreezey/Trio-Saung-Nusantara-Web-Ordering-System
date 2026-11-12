// logic login kasir dan admin
document.addEventListener('DOMContentLoaded', function () {
    const email = document.getElementById('email');
    const pass = document.getElementById('password');
    const eyeBtn = document.querySelector('.eye-btn');
    const eyeIcon = eyeBtn.querySelector('span')
    const loginForm = document.getElementById('loginForm');
    const errorMsg = document.getElementById('error-msg');

    eyeBtn.addEventListener('click', function(){
        // ganti tipe password 
        const isPassword = pass.getAttribute('type') === 'password';
        pass.setAttribute('type', isPassword ? 'text' : 'password');

        if (isPassword) {
            eyeIcon.classList.remove('btn-visible');
            eyeIcon.classList.add('btn-not-visible');
        } else {
            eyeIcon.classList.remove('btn-not-visible');
            eyeIcon.classList.add('btn-visible');
        }
    });

    // Dummy data untuk simulasi login kasir & admin
    const registeredUsers = [
        { email: 'admin@saung.com', password: 'password123', role: 'Admin' },
        { email: 'kasir@saung.com', password: 'password123', role: 'Kasir' }
    ];

    // tampilin pesan error dalam login card
    function showError(message) {
        errorMsg.textContent = message;
        errorMsg.classList.remove('hidden');
    }

    // hide pesan error
    function hideError() {
        errorMsg.textContent = '';
        errorMsg.classList.add('hidden');
    }

    // sembunyikan error saat user mulai mengetik ulang
    email.addEventListener('input', hideError);
    pass.addEventListener('input', hideError);

    // Logika Validasi Submit Form
    loginForm.addEventListener('submit', function (e) {
        e.preventDefault();
        hideError(); // Reset pesan error sebelumnya

        const emailVal = email.value.trim();
        const passVal = pass.value.trim();
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        // 1. Validasi Input Kosong
        if (!emailVal) {
            showError('Silakan masukkan alamat email Anda.');
            return;
        }

        if (!passVal) {
            showError('Silakan masukkan kata sandi Anda.');
            return;
        }

        // 2. Validasi Format Email
        if (!emailPattern.test(emailVal)) {
            showError('Format email yang Anda masukkan tidak valid.');
            return;
        }

        // 3. Validasi Panjang Minimal Password
        if (passVal.length < 8) {
            showError('Kata sandi harus terdiri dari minimal 8 karakter.');
            return;
        }

        // 4. Validasi Kredensial (Email & Password)
        const foundUser = registeredUsers.find(user => user.email === emailVal);

        if (!foundUser) {
            showError('Email tidak terdaftar. Periksa kembali email Anda.');
            return;
        }

        if (foundUser.password !== passVal) {
            showError('Kata sandi yang Anda masukkan salah.');
            return;
        }

        // Jika Berhasil Login
        alert(`Login Berhasil! Selamat datang, ${foundUser.role}.`);
        // window.location.href = foundUser.role === 'Admin' ? '../admin/dashboard.html' : '../kasir/pos.html';
    });
});