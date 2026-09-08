/**
 * Inventory Management Dashboard Application Logic
 * Supports Authentication, Role Protection, and User Management
 */

// Initialize Telegram WebApp if available
if (window.Telegram && window.Telegram.WebApp) {
    try {
        window.Telegram.WebApp.ready();
        window.Telegram.WebApp.expand();
    } catch (e) {
        console.log("Telegram WebApp not active");
    }
}

// Global State
let currentUser = null;
let allProducts = [];
let allUsers = [];
let categoriesSet = new Set();
let pendingDeleteId = null;

// DOM Elements
const userDisplayName = document.getElementById('user-display-name');
const userDisplayRole = document.getElementById('user-display-role');
const btnLogout = document.getElementById('btn-logout');

const statTotalProducts = document.getElementById('stat-total-products');
const statLowStock = document.getElementById('stat-low-stock');
const statStockIn = document.getElementById('stat-stock-in');
const statStockOut = document.getElementById('stat-stock-out');
const statTotalVal = document.getElementById('stat-total-val');
const cardTotalCost = document.getElementById('card-total-cost');
const tabBtnUsers = document.getElementById('tab-btn-users');

const productsTableBody = document.getElementById('products-table-body');
const txTableBody = document.getElementById('tx-table-body');
const usersTableBody = document.getElementById('users-table-body');
const inputSearch = document.getElementById('input-search');
const selectCategory = document.getElementById('select-category');
const toastContainer = document.getElementById('toast-container');

// ==========================================
// Toast Notification Utility
// ==========================================
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : 'ℹ️');
    toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(50px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

// ==========================================
// Authentication & Initialization
// ==========================================

async function checkAuth() {
    try {
        const res = await fetch('/api/me');
        if (!res.ok) {
            window.location.href = '/login';
            return false;
        }
        currentUser = await res.json();

        // Update Navbar User Info
        userDisplayName.textContent = currentUser.full_name || currentUser.username;
        const isAdmin = currentUser.role === 'admin';
        userDisplayRole.textContent = isAdmin ? '👑 Admin' : '👷 Staff';
        userDisplayRole.className = `badge ${isAdmin ? 'badge-danger' : 'badge-info'}`;

        // Show/Hide Admin-Only elements
        if (isAdmin) {
            if (tabBtnUsers) tabBtnUsers.style.display = 'inline-block';
            if (cardTotalCost) cardTotalCost.style.display = 'flex';
        } else {
            if (tabBtnUsers) tabBtnUsers.style.display = 'none';
            if (cardTotalCost) cardTotalCost.style.display = 'none';
            // Hide cost in edit modal
            const editCostGroup = document.getElementById('edit-cost')?.closest('.form-group');
            if (editCostGroup) editCostGroup.style.display = 'none';
        }

        return true;
    } catch (err) {
        window.location.href = '/login';
        return false;
    }
}

btnLogout.addEventListener('click', async () => {
    try {
        await fetch('/api/logout', { method: 'POST' });
        window.location.href = '/login';
    } catch (err) {
        window.location.href = '/login';
    }
});

// ==========================================
// API Calls & Data Fetching
// ==========================================

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();

        statTotalProducts.textContent = data.total_products;
        statLowStock.textContent = data.low_stock_count;
        statStockIn.textContent = data.daily_summary.stock_in.quantity;
        statStockOut.textContent = data.daily_summary.stock_out.quantity;

        if (data.is_admin) {
            statTotalVal.textContent = `$${data.total_asset_cost.toFixed(2)}`;
        }
    } catch (err) {
        console.error('Error fetching stats:', err);
    }
}

async function fetchProducts() {
    try {
        const res = await fetch('/api/products');
        if (!res.ok) throw new Error('Failed to fetch products');
        allProducts = await res.json();

        // Populate Categories Set
        categoriesSet.clear();
        allProducts.forEach(p => {
            if (p.category) categoriesSet.add(p.category);
        });
        updateCategoryOptions();

        renderProductsTable();
    } catch (err) {
        console.error('Error fetching products:', err);
        productsTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-5 text-danger">
                    ❌ មានបញ្ហាក្នុងការទាញយកទិន្នន័យទំនិញ!
                </td>
            </tr>
        `;
    }
}

async function fetchTransactions() {
    try {
        const res = await fetch('/api/transactions?limit=25');
        if (!res.ok) throw new Error('Failed to fetch transactions');
        const txs = await res.json();
        renderTransactionsTable(txs);
    } catch (err) {
        console.error('Error fetching transactions:', err);
    }
}

async function fetchUsers() {
    if (!currentUser || currentUser.role !== 'admin') return;
    try {
        const res = await fetch('/api/users');
        if (!res.ok) throw new Error('Failed to fetch users');
        allUsers = await res.json();
        renderUsersTable(allUsers);
    } catch (err) {
        console.error('Error fetching users:', err);
    }
}

// ==========================================
// Rendering Functions
// ==========================================

function updateCategoryOptions() {
    const currentVal = selectCategory.value;
    selectCategory.innerHTML = `<option value="all">ប្រភេទទាំងអស់ (All)</option>`;
    categoriesSet.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        opt.textContent = cat;
        if (cat === currentVal) opt.selected = true;
        selectCategory.appendChild(opt);
    });
}

function renderProductsTable() {
    const query = inputSearch.value.trim().toLowerCase();
    const selectedCat = selectCategory.value;
    const isAdmin = currentUser && currentUser.role === 'admin';

    const filtered = allProducts.filter(p => {
        const matchesQuery = !query ||
            p.name.toLowerCase().includes(query) ||
            p.code.toLowerCase().includes(query) ||
            (p.category && p.category.toLowerCase().includes(query));
        const matchesCat = selectedCat === 'all' || p.category === selectedCat;
        return matchesQuery && matchesCat;
    });

    if (filtered.length === 0) {
        productsTableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-5 text-muted">
                    📭 មិនមានទំនិញត្រូវនឹងលក្ខខណ្ឌស្វែងរកឡើយ។
                </td>
            </tr>
        `;
        return;
    }

    productsTableBody.innerHTML = filtered.map(p => {
        const isLow = p.quantity <= p.min_quantity;
        const statusBadge = isLow
            ? `<span class="badge badge-danger">⚠️ ជិតអស់ (${p.quantity} ≤ ${p.min_quantity})</span>`
            : `<span class="badge badge-success">✅ គ្រប់គ្រាន់</span>`;

        const costDisplay = isAdmin ? `$${p.cost_price.toFixed(2)}` : `<span class="text-muted">🔒 សម្ងាត់</span>`;
        const deleteBtn = isAdmin ? `<button class="btn btn-danger btn-sm" onclick="openDeleteModal(${p.id})">🗑️</button>` : '';

        return `
            <tr>
                <td><span class="badge badge-code">${escapeHtml(p.code)}</span></td>
                <td><strong>${escapeHtml(p.name)}</strong></td>
                <td><span class="badge badge-info">${escapeHtml(p.category || 'ទូទៅ')}</span></td>
                <td><strong>${p.quantity}</strong> <small class="text-muted">${escapeHtml(p.unit || 'ឯកតា')}</small></td>
                <td>${costDisplay}</td>
                <td><strong style="color: #818cf8;">$${p.sell_price.toFixed(2)}</strong></td>
                <td>${escapeHtml(p.location || 'ឃ្លាំងធំ')}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-success btn-sm" onclick="openStockInModal(${p.id})">📥 នាំចូល</button>
                        <button class="btn btn-warning btn-sm" onclick="openStockOutModal(${p.id})">📤 នាំចេញ</button>
                        <button class="btn btn-secondary btn-sm" onclick="openEditModal(${p.id})">✏️</button>
                        ${deleteBtn}
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function renderTransactionsTable(txs) {
    if (!txs || txs.length === 0) {
        txTableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-5 text-muted">
                    📭 មិនទាន់មានប្រវត្តិប្រតិបត្តិការនៅឡើយទេ។
                </td>
            </tr>
        `;
        return;
    }

    const isAdmin = currentUser && currentUser.role === 'admin';

    txTableBody.innerHTML = txs.map(t => {
        const isIN = t.type === 'IN';
        const typeBadge = isIN
            ? `<span class="badge badge-success">📥 នាំចូល</span>`
            : `<span class="badge badge-warning">📤 នាំចេញ</span>`;
        const sign = isIN ? '+' : '-';
        const dateStr = t.created_at ? t.created_at.substring(0, 16) : '';
        const priceStr = (!isIN || isAdmin) ? `$${t.unit_price.toFixed(2)}` : '🔒';
        const totalStr = (!isIN || isAdmin) ? `$${t.total_price.toFixed(2)}` : '🔒';

        return `
            <tr>
                <td class="small text-muted">${dateStr}</td>
                <td>${typeBadge}</td>
                <td><strong>${escapeHtml(t.product_name)}</strong> <small class="text-muted">(${escapeHtml(t.product_code)})</small></td>
                <td><strong>${sign}${t.quantity}</strong> ${escapeHtml(t.product_unit)}</td>
                <td>${priceStr}</td>
                <td><strong>${totalStr}</strong></td>
                <td>${escapeHtml(t.reference || '-')}</td>
                <td class="small">${escapeHtml(t.user_name || 'Admin')}</td>
            </tr>
        `;
    }).join('');
}

function renderUsersTable(users) {
    if (!users || users.length === 0) {
        usersTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-5 text-muted">
                    📭 មិនទាន់មានគណនីផ្សេងទៀតឡើយ។
                </td>
            </tr>
        `;
        return;
    }

    usersTableBody.innerHTML = users.map(u => {
        const isMaster = u.username === 'admin';
        const roleBadge = u.role === 'admin'
            ? `<span class="badge badge-danger">👑 Admin</span>`
            : `<span class="badge badge-info">👷 Staff</span>`;

        const deleteAction = isMaster
            ? `<span class="text-muted small">🔒 មេ Admin</span>`
            : `<button class="btn btn-danger btn-sm" onclick="deleteUser(${u.user_id}, '${escapeHtml(u.username)}')">🗑️ លុប</button>`;

        const dateStr = u.created_at ? u.created_at.substring(0, 10) : '-';

        return `
            <tr>
                <td><code>#${u.user_id}</code></td>
                <td><strong>${escapeHtml(u.full_name)}</strong></td>
                <td><code>@${escapeHtml(u.username)}</code></td>
                <td>${roleBadge}</td>
                <td class="small text-muted">${dateStr}</td>
                <td style="text-align: right;">${deleteAction}</td>
            </tr>
        `;
    }).join('');
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ==========================================
// Modal Operations
// ==========================================

function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('show');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('show');
}

// Close modals when clicking backdrop or close buttons
document.querySelectorAll('[data-close]').forEach(btn => {
    btn.addEventListener('click', () => {
        const targetId = btn.getAttribute('data-close');
        closeModal(targetId);
    });
});

document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.classList.remove('show');
        }
    });
});

// 1. Add Product
document.getElementById('btn-open-add-modal').addEventListener('click', () => {
    document.getElementById('form-add-product').reset();
    openModal('modal-add-product');
});

document.getElementById('form-add-product').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        code: formData.get('code').trim(),
        name: formData.get('name').trim(),
        category: formData.get('category').trim() || 'ទូទៅ',
        unit: formData.get('unit').trim() || 'ឯកតា',
        cost_price: parseFloat(formData.get('cost_price')) || 0,
        sell_price: parseFloat(formData.get('sell_price')) || 0,
        quantity: parseInt(formData.get('quantity')) || 0,
        min_quantity: parseInt(formData.get('min_quantity')) || 5,
        location: formData.get('location').trim() || 'ឃ្លាំងធំ'
    };

    try {
        const res = await fetch('/api/products', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        closeModal('modal-add-product');
        showToast(`🎉 បានបង្កើតទំនិញ '${data.name}' ដោយជោគជ័យ!`);
        fetchStats();
        fetchProducts();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 2. Stock In Modal
window.openStockInModal = function(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    document.getElementById('in-product-id').value = product.id;
    document.getElementById('in-product-title').textContent = `ទំនិញ៖ ${product.name} (ស្តុកបច្ចុប្បន្ន: ${product.quantity} ${product.unit})`;
    document.getElementById('in-unit-price').value = (currentUser.role === 'admin') ? product.cost_price.toFixed(2) : '0.00';
    openModal('modal-stock-in');
};

document.getElementById('form-stock-in').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        product_id: parseInt(formData.get('product_id')),
        quantity: parseInt(formData.get('quantity')),
        unit_price: parseFloat(formData.get('unit_price')) || 0,
        reference: formData.get('reference').trim() || 'នាំចូលតាម Web'
    };

    try {
        const res = await fetch('/api/stock-in', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        closeModal('modal-stock-in');
        showToast(`📥 នាំចូល +${data.quantity} ជោគជ័យ!`);
        fetchStats();
        fetchProducts();
        fetchTransactions();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 3. Stock Out Modal
window.openStockOutModal = function(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    document.getElementById('out-product-id').value = product.id;
    document.getElementById('out-product-title').textContent = `ទំនិញ៖ ${product.name} (ស្តុកនៅសល់: ${product.quantity} ${product.unit})`;
    document.getElementById('out-unit-price').value = product.sell_price.toFixed(2);
    openModal('modal-stock-out');
};

document.getElementById('form-stock-out').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        product_id: parseInt(formData.get('product_id')),
        quantity: parseInt(formData.get('quantity')),
        unit_price: parseFloat(formData.get('unit_price')) || 0,
        reference: formData.get('reference').trim() || 'លក់ចេញតាម Web'
    };

    try {
        const res = await fetch('/api/stock-out', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        closeModal('modal-stock-out');
        showToast(`📤 កាត់ស្តុក -${data.quantity} ជោគជ័យ!`);
        fetchStats();
        fetchProducts();
        fetchTransactions();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 4. Edit Product Modal
window.openEditModal = function(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    document.getElementById('edit-product-id').value = product.id;
    document.getElementById('edit-name').value = product.name;
    document.getElementById('edit-category').value = product.category;
    document.getElementById('edit-unit').value = product.unit;
    document.getElementById('edit-cost').value = product.cost_price;
    document.getElementById('edit-sell').value = product.sell_price;
    document.getElementById('edit-min-qty').value = product.min_quantity;
    document.getElementById('edit-location').value = product.location;
    openModal('modal-edit-product');
};

document.getElementById('form-edit-product').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const productId = formData.get('product_id');
    const data = {
        name: formData.get('name').trim(),
        category: formData.get('category').trim(),
        unit: formData.get('unit').trim(),
        cost_price: parseFloat(formData.get('cost_price')) || 0,
        sell_price: parseFloat(formData.get('sell_price')) || 0,
        min_quantity: parseInt(formData.get('min_quantity')) || 0,
        location: formData.get('location').trim()
    };

    try {
        const res = await fetch(`/api/products/${productId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        closeModal('modal-edit-product');
        showToast(`✅ បានកែប្រែព័ត៌មាន '${data.name}' ជោគជ័យ!`);
        fetchStats();
        fetchProducts();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 5. Delete Modal
window.openDeleteModal = function(productId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;
    pendingDeleteId = product.id;
    document.getElementById('delete-prompt-text').textContent = `តើបងពិតជាចង់លុបទំនិញ '${product.name}' (កូដ: ${product.code}) មែនទេ?`;
    openModal('modal-delete-confirm');
};

document.getElementById('btn-confirm-delete').addEventListener('click', async () => {
    if (!pendingDeleteId) return;
    try {
        const res = await fetch(`/api/products/${pendingDeleteId}`, {
            method: 'DELETE'
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        closeModal('modal-delete-confirm');
        showToast('🗑️ បានលុបទំនិញដោយជោគជ័យ!');
        pendingDeleteId = null;
        fetchStats();
        fetchProducts();
        fetchTransactions();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 6. User Management Operations (Admin Only)
const btnOpenAddUser = document.getElementById('btn-open-add-user-modal');
if (btnOpenAddUser) {
    btnOpenAddUser.addEventListener('click', () => {
        document.getElementById('form-add-user').reset();
        const newUserPwdInput = document.getElementById('new-user-pwd');
        if (newUserPwdInput) newUserPwdInput.type = 'password';
        const btnToggle = document.getElementById('btn-toggle-new-user-pwd');
        if (btnToggle) {
            const eyeOpen = btnToggle.querySelector('.eye-open');
            const eyeClosed = btnToggle.querySelector('.eye-closed');
            if (eyeOpen) eyeOpen.style.display = 'block';
            if (eyeClosed) eyeClosed.style.display = 'none';
        }
        openModal('modal-add-user');
    });
}

const btnToggleNewUserPwd = document.getElementById('btn-toggle-new-user-pwd');
const newUserPwdInput = document.getElementById('new-user-pwd');
if (btnToggleNewUserPwd && newUserPwdInput) {
    const eyeOpen = btnToggleNewUserPwd.querySelector('.eye-open');
    const eyeClosed = btnToggleNewUserPwd.querySelector('.eye-closed');
    btnToggleNewUserPwd.addEventListener('click', () => {
        const isPassword = newUserPwdInput.type === 'password';
        newUserPwdInput.type = isPassword ? 'text' : 'password';
        if (eyeOpen) eyeOpen.style.display = isPassword ? 'none' : 'block';
        if (eyeClosed) eyeClosed.style.display = isPassword ? 'block' : 'none';
    });
}

const formAddUser = document.getElementById('form-add-user');
if (formAddUser) {
    formAddUser.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            full_name: formData.get('full_name').trim(),
            username: formData.get('username').trim().toLowerCase(),
            role: formData.get('role'),
            password: formData.get('password')
        };

        if (data.password.length < 4) {
            showToast('លេខសម្ងាត់ត្រូវមានយ៉ាងតិច ៤ តួ!', 'error');
            return;
        }

        try {
            const res = await fetch('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await res.json();
            if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

            closeModal('modal-add-user');
            showToast(`🎉 បានបង្កើតគណនី '${data.username}' ដោយជោគជ័យ!`);
            fetchUsers();
        } catch (err) {
            showToast(err.message, 'error');
        }
    });
}

window.deleteUser = async function(userId, username) {
    if (!confirm(`តើបងពិតជាចង់លុបគណនី '${username}' មែនទេ?`)) return;

    try {
        const res = await fetch(`/api/users/${userId}`, { method: 'DELETE' });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');

        showToast(`🗑️ បានលុបគណនី '${username}' រួចរាល់!`);
        fetchUsers();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

// ==========================================
// Tabs & Events
// ==========================================

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));

        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        const pane = document.getElementById(targetId);
        if (pane) pane.classList.add('active');

        if (targetId === 'tab-transactions') {
            fetchTransactions();
        } else if (targetId === 'tab-users') {
            fetchUsers();
            fetchGoogleSheetsConfig();
        }
    });
});

async function fetchGoogleSheetsConfig() {
    if (!currentUser || currentUser.role !== 'admin') return;
    try {
        const res = await fetch('/api/settings/google-sheets');
        if (!res.ok) return;
        const data = await res.json();
        const inputUrl = document.getElementById('gsheet-webhook-url');
        const badge = document.getElementById('gsheet-status-badge');
        if (inputUrl && data.webhook_url) {
            inputUrl.value = data.webhook_url;
        }
        if (badge) {
            badge.style.display = data.is_configured ? 'inline-block' : 'none';
        }
    } catch (err) {
        console.error('Error fetching Google Sheets config:', err);
    }
}

const formGsheetConfig = document.getElementById('form-gsheet-config');
if (formGsheetConfig) {
    formGsheetConfig.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = document.getElementById('gsheet-webhook-url').value.trim();
        try {
            const res = await fetch('/api/settings/google-sheets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ webhook_url: url })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'បរាជ័យ');
            showToast('✅ បានរក្សាទុក Google Sheets Webhook រួចរាល់!');
            fetchGoogleSheetsConfig();
        } catch (err) {
            showToast(err.message, 'error');
        }
    });
}

inputSearch.addEventListener('input', renderProductsTable);
selectCategory.addEventListener('change', renderProductsTable);

document.getElementById('btn-refresh-products').addEventListener('click', () => {
    fetchStats();
    fetchProducts();
    showToast('🔄 បានផ្ទុកទិន្នន័យថ្មីរួចរាល់');
});

document.getElementById('btn-refresh-tx').addEventListener('click', () => {
    fetchTransactions();
    showToast('🔄 បានផ្ទុកប្រវត្តិថ្មីរួចរាល់');
});

const btnTestAlert = document.getElementById('btn-test-telegram-alert');
if (btnTestAlert) {
    btnTestAlert.addEventListener('click', async () => {
        const statusSpan = document.getElementById('alert-test-status');
        btnTestAlert.disabled = true;
        btnTestAlert.innerHTML = '<span>⏳ កំពុងផ្ញើ...</span>';
        if (statusSpan) statusSpan.textContent = '';

        try {
            const res = await fetch('/api/settings/telegram-alerts/test', { method: 'POST' });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'បរាជ័យក្នុងការផ្ញើសារ');
            showToast('🎉 បានផ្ញើសារ Alert តេស្តទៅ Telegram រួចរាល់! សូមពិនិត្យមើល Bot របស់អ្នក។');
            if (statusSpan) {
                statusSpan.textContent = '✅ បានផ្ញើជោគជ័យ!';
                statusSpan.style.color = '#10b981';
            }
        } catch (err) {
            showToast(err.message, 'error');
            if (statusSpan) {
                statusSpan.textContent = '❌ ' + err.message;
                statusSpan.style.color = '#ef4444';
            }
        } finally {
            btnTestAlert.disabled = false;
            btnTestAlert.innerHTML = '<span>📢 ធ្វើតេស្តផ្ញើសារ Alert ទៅ Telegram</span>';
        }
    });
}

// Initial boot
(async () => {
    const isOk = await checkAuth();
    if (isOk) {
        fetchStats();
        fetchProducts();
    }
})();
