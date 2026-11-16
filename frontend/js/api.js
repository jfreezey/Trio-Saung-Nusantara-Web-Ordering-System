
const API_BASE_URL = "http://127.0.0.1:8000/api";

async function getMenus() {
    const response = await fetch(`${API_BASE_URL}/menus`);

    if (!response.ok) {
        throw new Error("Gagal mengambil data menu");
    }

    const result = await response.json();

    return result.data;
}

async function getCategories() {
    const response = await fetch(`${API_BASE_URL}/categories`);

    if (!response.ok) {
        throw new Error("Gagal mengambil data kategori");
    }

    const result = await response.json();

    return result.data;
}
