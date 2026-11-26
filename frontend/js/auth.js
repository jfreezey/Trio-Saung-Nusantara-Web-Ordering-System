document.addEventListener('DOMContentLoaded', function () {
    const email = document.getElementById('email');
    const pass = document.getElementById('password');
    const eyeBtn = document.querySelector('.eye-btn');
    const eyeIcon = eyeBtn.querySelector('span');
    const loginForm = document.getElementById('loginForm');
    const errorMsg = document.getElementById('error-msg');

    // Tampilkan atau sembunyikan password
    eyeBtn.addEventListener('click', function () {
        const isPassword = pass.getAttribute('type') === 'password';

        pass.setAttribute('type', isPassword ? 'text' : 'password');

        if (isPassword) {
            eyeIcon.classList.remove('btn-not-visible');
            eyeIcon.classList.add('btn-visible');
        } else {
            eyeIcon.classList.remove('btn-visible');
            eyeIcon.classList.add('btn-not-visible');
        }
    });

    // Tampilkan pesan error
    function showError(message) {
        errorMsg.textContent = message;
        errorMsg.classList.remove('hidden');
    }

    // Sembunyikan pesan error
    function hideError() {
        errorMsg.textContent = '';
        errorMsg.classList.add('hidden');
    }

    // Sembunyikan error saat pengguna mengetik
    email.addEventListener('input', hideError);
    pass.addEventListener('input', hideError);

    // Proses login menggunakan backend
    loginForm.addEventListener('submit', async function (e) {
        e.preventDefault();
        hideError();

        const emailVal = email.value.trim();
        const passVal = pass.value;

        // Validasi input kosong
        if (!emailVal) {
            showError('Silakan masukkan alamat email Anda.');
            return;
        }

        if (!passVal) {
            showError('Silakan masukkan kata sandi Anda.');
            return;
        }

        // Validasi format email
        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailPattern.test(emailVal)) {
            showError('Format email yang Anda masukkan tidak valid.');
            return;
        }

        try {
            // Kirim email dan password ke backend
         const result = await loginUser(emailVal, passVal);

        // Ambil data dari respons backend
        const loginData = result.data;

        // Simpan access token
        localStorage.setItem('access_token', loginData.access_token);

        // Ambil role pengguna
        const role = loginData.user.role;

        // Arahkan berdasarkan role
        if (role === 'admin') {
            window.location.href = '/frontend/components/admin/dashboard.html';

        } else if (role === 'cashier') {
            window.location.href = '/frontend/components/kasir/dashboard.html';

        } else {
            showError('Role pengguna tidak dikenali.');
        }

        } catch (error) {
            showError(error.message || 'Login gagal. Silakan coba lagi.');
        }
    });
});
