document.addEventListener("DOMContentLoaded", function () {
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const loginForm = document.getElementById("loginForm");
    const errorMsg = document.getElementById("error-msg");
    const eyeBtn = document.querySelector(".eye-btn");
    const eyeIcon = eyeBtn?.querySelector("span");

    if (!emailInput || !passwordInput || !loginForm || !errorMsg) {
        console.error("Elemen form login tidak lengkap.");
        return;
    }

    const submitButton = loginForm.querySelector(
        'button[type="submit"], input[type="submit"]'
    );

    let submitting = false;

    function showError(message) {
        errorMsg.textContent = message;
        errorMsg.classList.remove("hidden");
    }

    function hideError() {
        errorMsg.textContent = "";
        errorMsg.classList.add("hidden");
    }

    emailInput.addEventListener("input", hideError);
    passwordInput.addEventListener("input", hideError);

    // Tombol tampilkan/sembunyikan password.
    if (eyeBtn) {
        eyeBtn.addEventListener("click", function (event) {
            event.preventDefault();

            const showPassword = passwordInput.type === "password";
            passwordInput.type = showPassword ? "text" : "password";

            if (eyeIcon) {
                eyeIcon.classList.toggle("btn-visible", !showPassword);
                eyeIcon.classList.toggle("btn-not-visible", showPassword);
            }
        });
    }

    loginForm.addEventListener("submit", async function (event) {
        event.preventDefault();

        if (submitting) {
            return;
        }

        hideError();

        const email = emailInput.value.trim().toLowerCase();

        const password = passwordInput.value;

        if (!email || !password) {
            showError("Silakan isi email dan kata sandi.");
            return;
        }

        submitting = true;

        if (submitButton) {
            submitButton.disabled = true;
        }

        try {
            const response = await fetch("/api/login", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    email: email,
                    password: password,
                }),
            });

            const data = await response.json();

            if (!response.ok) {
                const message =
                    typeof data.detail === "string"
                        ? data.detail
                        : "Login gagal. Periksa email dan kata sandi.";

                showError(message);
                return;
            }

            if (data.user?.role === "admin") {
                window.location.replace(
                    "/frontend/components/admin/dashboard.html"
                );
            } else if (data.user?.role === "cashier") {
                window.location.replace(
                    "/frontend/components/kasir/dashboard.html"
                );
            } else {
                showError("Role akun tidak dikenali.");
            }
        } catch (error) {
            showError(
                "Tidak dapat menghubungi backend. " +
                "Pastikan server Python berjalan dan website dibuka lewat port 8000."
            );
        } finally {
            submitting = false;

            if (submitButton) {
                submitButton.disabled = false;
            }
        }
    });
});