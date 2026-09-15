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
const selectExpiryFilter = document.getElementById('select-expiry-filter');
const toastContainer = document.getElementById('toast-container');

// Transactions filter state (Calendar / Date range)
const txFilter = { date_from: '', date_to: '', type: '', search: '' };
let calendarCursor = new Date();
let expiryBatchesCache = [];

const EXPIRY_WARN_DAYS = 30;

function todayISO() {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function dateToISO(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function daysUntil(isoDate) {
    if (!isoDate) return null;
    const [y, m, d] = isoDate.split('-').map(Number);
    const target = new Date(y, m - 1, d);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    return Math.round((target - today) / 86400000);
}

function expiryStatusOf(isoDate) {
    const days = daysUntil(isoDate);
    if (days === null) return 'none';
    if (days < 0) return 'expired';
    if (days <= EXPIRY_WARN_DAYS) return 'soon';
    return 'ok';
}

function expiryBadge(isoDate, qty, batchNo) {
    const days = daysUntil(isoDate);
    const qtyStr = (qty !== undefined && qty !== null) ? ` ×${qty}` : '';
    const lot = batchNo ? `<b>${escapeHtml(batchNo)}</b> · ` : '';
    if (days === null) return `<span class="badge badge-muted">— គ្មាន</span>`;
    if (days < 0) return `<span class="badge badge-danger">🔴 ${lot}${isoDate}${qtyStr} (ផុត ${Math.abs(days)} ថ្ងៃ)</span>`;
    if (days === 0) return `<span class="badge badge-danger">🔴 ${lot}${isoDate}${qtyStr} (ផុតថ្ងៃនេះ)</span>`;
    if (days <= EXPIRY_WARN_DAYS) return `<span class="badge badge-warning">🟠 ${lot}${isoDate}${qtyStr} (${days} ថ្ងៃទៀត)</span>`;
    return `<span class="badge badge-success">🟢 ${lot}${isoDate}${qtyStr} (${days} ថ្ងៃ)</span>`;
}

function daysLeftBadge(isoDate) {
    const days = daysUntil(isoDate);
    if (days === null) return `<span class="badge badge-muted">—</span>`;
    if (days < 0) return `<span class="badge badge-danger">ផុត ${Math.abs(days)} ថ្ងៃ</span>`;
    if (days === 0) return `<span class="badge badge-danger">ផុតថ្ងៃនេះ</span>`;
    if (days <= EXPIRY_WARN_DAYS) return `<span class="badge badge-warning">${days} ថ្ងៃទៀត</span>`;
    return `<span class="badge badge-success">${days} ថ្ងៃទៀត</span>`;
}

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

        const statExpired = document.getElementById('stat-expired');
        const statExpiring = document.getElementById('stat-expiring');
        if (statExpired) statExpired.textContent = data.expired_count ?? 0;
        if (statExpiring) statExpiring.textContent = data.expiring_soon_count ?? 0;
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

function txQueryString() {
    const params = new URLSearchParams();
    if (txFilter.date_from) params.set('date_from', txFilter.date_from);
    if (txFilter.date_to) params.set('date_to', txFilter.date_to);
    if (txFilter.type) params.set('type', txFilter.type);
    if (txFilter.search) params.set('search', txFilter.search);
    return params.toString();
}

function syncTxFilterUI() {
    document.getElementById('tx-date-from').value = txFilter.date_from;
    document.getElementById('tx-date-to').value = txFilter.date_to;
    document.getElementById('tx-type-filter').value = txFilter.type;
    document.getElementById('tx-search').value = txFilter.search;

    const qs = txQueryString();
    const exportLink = document.getElementById('btn-export-tx-csv');
    if (exportLink) exportLink.href = '/api/export/transactions/csv' + (qs ? '?' + qs : '');

    const label = document.getElementById('tx-filter-label');
    if (label) {
        const parts = [];
        if (txFilter.date_from || txFilter.date_to) {
            parts.push(`📅 ${txFilter.date_from || '...'} → ${txFilter.date_to || '...'}`);
        }
        if (txFilter.type) parts.push(txFilter.type === 'IN' ? 'តែនាំចូល' : 'តែនាំចេញ');
        if (txFilter.search) parts.push(`🔍 "${txFilter.search}"`);
        label.textContent = parts.length ? `តម្រង៖ ${parts.join(' · ')}` : 'បង្ហាញប្រតិបត្តិការចុងក្រោយទាំងអស់';
    }
}

async function fetchTransactions() {
    syncTxFilterUI();
    const qs = txQueryString();
    const hasFilter = !!qs;
    try {
        const [resTx, resSum] = await Promise.all([
            fetch(`/api/transactions?limit=${hasFilter ? 2000 : 50}${qs ? '&' + qs : ''}`),
            fetch(`/api/transactions/summary${qs ? '?' + qs : ''}`)
        ]);
        if (!resTx.ok) throw new Error('Failed to fetch transactions');
        const txs = await resTx.json();
        renderTransactionsTable(txs);
        if (resSum.ok) renderTxSummary(await resSum.json());
    } catch (err) {
        console.error('Error fetching transactions:', err);
    }
}

function renderTxSummary(sum) {
    const isAdmin = currentUser && currentUser.role === 'admin';
    document.getElementById('tx-sum-in-qty').textContent = sum.IN.quantity;
    document.getElementById('tx-sum-in-count').textContent = sum.IN.transactions;
    document.getElementById('tx-sum-out-qty').textContent = sum.OUT.quantity;
    document.getElementById('tx-sum-out-count').textContent = sum.OUT.transactions;
    document.getElementById('tx-sum-in-amt').textContent = isAdmin ? `· $${Number(sum.IN.amount).toFixed(2)}` : '';
    document.getElementById('tx-sum-out-amt').textContent = `· $${Number(sum.OUT.amount).toFixed(2)}`;
}

function setQuickRange(range) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    let from = '', to = '';
    if (range === 'today') { from = to = dateToISO(today); }
    else if (range === 'yesterday') { const y = new Date(today); y.setDate(y.getDate() - 1); from = to = dateToISO(y); }
    else if (range === 'week') { const w = new Date(today); w.setDate(w.getDate() - 6); from = dateToISO(w); to = dateToISO(today); }
    else if (range === 'month') { from = dateToISO(new Date(today.getFullYear(), today.getMonth(), 1)); to = dateToISO(today); }
    else if (range === 'lastmonth') {
        from = dateToISO(new Date(today.getFullYear(), today.getMonth() - 1, 1));
        to = dateToISO(new Date(today.getFullYear(), today.getMonth(), 0));
    }
    else if (range === 'clear') { txFilter.type = ''; txFilter.search = ''; }
    txFilter.date_from = from;
    txFilter.date_to = to;
    document.querySelectorAll('.filter-quick .btn').forEach(b => b.classList.toggle('active', b.dataset.range === range && range !== 'clear'));
    fetchTransactions();
}

function showTransactionsForDay(isoDate) {
    txFilter.date_from = isoDate;
    txFilter.date_to = isoDate;
    document.querySelectorAll('.filter-quick .btn').forEach(b => b.classList.remove('active'));
    switchTab('tab-transactions');
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

    const expiryFilter = selectExpiryFilter ? selectExpiryFilter.value : 'all';

    const filtered = allProducts.filter(p => {
        const matchesQuery = !query ||
            p.name.toLowerCase().includes(query) ||
            p.code.toLowerCase().includes(query) ||
            (p.category && p.category.toLowerCase().includes(query));
        const matchesCat = selectedCat === 'all' || p.category === selectedCat;
        let matchesExp = true;
        if (expiryFilter === 'expired') matchesExp = (p.expired_qty || 0) > 0;
        else if (expiryFilter === 'soon') matchesExp = (p.expiring_qty || 0) > 0;
        else if (expiryFilter === 'ok') matchesExp = !!p.nearest_expiry && (p.expired_qty || 0) === 0 && (p.expiring_qty || 0) === 0;
        else if (expiryFilter === 'none') matchesExp = !p.nearest_expiry;
        return matchesQuery && matchesCat && matchesExp;
    });

    if (filtered.length === 0) {
        productsTableBody.innerHTML = `
            <tr>
                <td colspan="10" class="text-center py-5 text-muted">
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

        const batches = p.batches || [];
        let expiryCell;
        if (batches.length === 0) {
            expiryCell = `<span class="badge badge-muted">— គ្មាន</span>`;
        } else {
            const first = batches[0];
            const more = batches.length > 1 ? `<span class="expiry-more">+${batches.length - 1} ឡូតិ៍</span>` : '';
            expiryCell = `${expiryBadge(first.expiry_date, first.quantity, first.batch_no)}${more}`;
        }
        const expiryTd = `<td class="expiry-cell" onclick="openBatchesModal(${p.id})" title="ចុចដើម្បីមើល/គ្រប់គ្រងឡូតិ៍ផុតកំណត់ទាំងអស់">${expiryCell}</td>`;

        return `
            <tr>
                <td><span class="badge badge-code">${escapeHtml(p.code)}</span></td>
                <td><strong>${escapeHtml(p.name)}</strong></td>
                <td><span class="badge badge-info">${escapeHtml(p.category || 'ទូទៅ')}</span></td>
                <td><strong>${p.quantity}</strong> <small class="text-muted">${escapeHtml(p.unit || 'ឯកតា')}</small></td>
                ${expiryTd}
                <td>${costDisplay}</td>
                <td><strong style="color: #818cf8;">$${p.sell_price.toFixed(2)}</strong></td>
                <td>${escapeHtml(p.location || 'ឃ្លាំងធំ')}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-success btn-sm" onclick="openStockInModal(${p.id})">📥 នាំចូល</button>
                        <button class="btn btn-warning btn-sm" onclick="openStockOutModal(${p.id})">📤 នាំចេញ</button>
                        <button class="btn btn-secondary btn-sm" onclick="openBatchesModal(${p.id})" title="ឡូតិ៍ / ថ្ងៃផុតកំណត់">⏰</button>
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
                <td colspan="9" class="text-center py-5 text-muted">
                    📭 មិនមានប្រតិបត្តិការត្រូវនឹងតម្រងនេះទេ។
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
                <td class="small">${t.expiry_date ? expiryBadge(t.expiry_date, null, t.batch_no) : '<span class="text-muted">—</span>'}</td>
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
        location: formData.get('location').trim() || 'ឃ្លាំងធំ',
        expiry_date: formData.get('expiry_date') || null,
        batch_no: (formData.get('batch_no') || '').trim() || null
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
    document.getElementById('in-expiry-date').value = '';
    document.getElementById('in-batch-no').value = '';
    const hint = document.getElementById('in-existing-batches');
    const batches = product.batches || [];
    hint.innerHTML = batches.length
        ? `ឡូតិ៍ដែលមានស្រាប់៖ ${batches.map(b => expiryBadge(b.expiry_date, b.quantity, b.batch_no)).join(' ')}<br><small>លេខឡូតិ៍ + ថ្ងៃផុតកំណត់ ដូចឡូតិ៍ស្រាប់ = បូកបញ្ចូលគ្នា; ខុសគ្នា = ឡូតិ៍ថ្មី។</small>`
        : `<small>ទំនិញនេះមិនទាន់មានឡូតិ៍ទេ — បញ្ចូលលេខឡូតិ៍ + ថ្ងៃផុតកំណត់ ដើម្បីតាមដាន (ទុកទទេបើគ្មាន)។</small>`;
    openModal('modal-stock-in');
};

document.getElementById('form-stock-in').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        product_id: parseInt(formData.get('product_id')),
        quantity: parseInt(formData.get('quantity')),
        unit_price: parseFloat(formData.get('unit_price')) || 0,
        reference: formData.get('reference').trim() || 'នាំចូលតាម Web',
        expiry_date: formData.get('expiry_date') || null,
        batch_no: (formData.get('batch_no') || '').trim() || null
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
        showToast(`📥 នាំចូល +${data.quantity} ជោគជ័យ!${data.expiry_date ? ' (' + (data.batch_no ? data.batch_no + ' · ' : '') + 'ផុតកំណត់ ' + data.expiry_date + ')' : ''}`);
        fetchStats();
        fetchProducts();
        fetchTransactions();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

// 3. Stock Out Modal
window.openStockOutModal = function(productId, preselectBatchId) {
    const product = allProducts.find(p => p.id === productId);
    if (!product) return;

    document.getElementById('out-product-id').value = product.id;
    document.getElementById('out-product-title').textContent = `ទំនិញ៖ ${product.name} (ស្តុកនៅសល់: ${product.quantity} ${product.unit})`;
    document.getElementById('out-unit-price').value = product.sell_price.toFixed(2);
    populateBatchSelect(product, preselectBatchId);
    openModal('modal-stock-out');
};

function populateBatchSelect(product, preselectBatchId) {
    const sel = document.getElementById('out-batch-select');
    const group = document.getElementById('out-batch-group');
    const batches = product.batches || [];
    sel.innerHTML = `<option value="">🔄 ស្វ័យប្រវត្តិ — ផុតកំណត់មុន ចេញមុន (FEFO)</option>`;
    batches.forEach(b => {
        const days = daysUntil(b.expiry_date);
        const tag = days < 0 ? '🔴 ផុតកំណត់' : (days <= EXPIRY_WARN_DAYS ? '🟠 ជិតផុត' : '🟢');
        const opt = document.createElement('option');
        opt.value = b.id;
        opt.textContent = `${tag} ${b.batch_no ? b.batch_no + ' · ' : ''}${b.expiry_date} — នៅសល់ ${b.quantity} ${product.unit || ''}`;
        if (preselectBatchId && Number(preselectBatchId) === b.id) opt.selected = true;
        sel.appendChild(opt);
    });
    group.style.display = batches.length ? 'block' : 'none';
}

document.getElementById('form-stock-out').addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
        product_id: parseInt(formData.get('product_id')),
        quantity: parseInt(formData.get('quantity')),
        unit_price: parseFloat(formData.get('unit_price')) || 0,
        reference: formData.get('reference').trim() || 'លក់ចេញតាម Web',
        batch_id: formData.get('batch_id') ? parseInt(formData.get('batch_id')) : null
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
        const ded = (result.product && result.product.batches_deducted) || [];
        const dedStr = ded.length ? ' — ពីឡូតិ៍: ' + ded.map(d => `${d.batch_no ? d.batch_no + ' ' : ''}${d.expiry_date} ×${d.quantity}`).join(', ') : '';
        showToast(`📤 កាត់ស្តុក -${data.quantity} ជោគជ័យ!${dedStr}`);
        fetchStats();
        fetchProducts();
        fetchTransactions();
        if (document.getElementById('tab-expiry').classList.contains('active')) fetchExpiry();
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
    document.getElementById('edit-batch-no').value = '';
    document.getElementById('edit-batch-expiry').value = '';
    document.getElementById('edit-batch-qty').value = 1;
    editBatchesProductId = product.id;
    loadBatchesTable(product.id, 'edit');
    openModal('modal-edit-product');
};

let editBatchesProductId = null;

document.getElementById('btn-edit-add-batch').addEventListener('click', () => {
    addBatchStockIn(
        editBatchesProductId,
        document.getElementById('edit-batch-no').value,
        document.getElementById('edit-batch-expiry').value,
        parseInt(document.getElementById('edit-batch-qty').value),
        'edit'
    );
});

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

function switchTab(targetId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.toggle('active', b.getAttribute('data-tab') === targetId));
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    const pane = document.getElementById(targetId);
    if (pane) pane.classList.add('active');

    if (targetId === 'tab-transactions') {
        fetchTransactions();
    } else if (targetId === 'tab-calendar') {
        renderCalendar();
    } else if (targetId === 'tab-expiry') {
        fetchExpiry();
    } else if (targetId === 'tab-users') {
        fetchUsers();
        fetchGoogleSheetsConfig();
    }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
});

const cardExpiry = document.getElementById('card-expiry');
if (cardExpiry) cardExpiry.addEventListener('click', () => switchTab('tab-expiry'));

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
if (selectExpiryFilter) selectExpiryFilter.addEventListener('change', renderProductsTable);

// ==========================================
// Transaction Filters (Date range / Calendar)
// ==========================================
document.getElementById('tx-date-from').addEventListener('change', (e) => { txFilter.date_from = e.target.value; fetchTransactions(); });
document.getElementById('tx-date-to').addEventListener('change', (e) => { txFilter.date_to = e.target.value; fetchTransactions(); });
document.getElementById('tx-type-filter').addEventListener('change', (e) => { txFilter.type = e.target.value; fetchTransactions(); });
let txSearchTimer = null;
document.getElementById('tx-search').addEventListener('input', (e) => {
    clearTimeout(txSearchTimer);
    txSearchTimer = setTimeout(() => { txFilter.search = e.target.value.trim(); fetchTransactions(); }, 350);
});
document.querySelectorAll('.filter-quick .btn').forEach(btn => {
    btn.addEventListener('click', () => setQuickRange(btn.dataset.range));
});

// ==========================================
// Calendar (Stock In / Out per day + Expiry)
// ==========================================
const KM_MONTHS = ['មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា', 'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ'];
const KM_DAYS = ['អាទិត្យ', 'ចន្ទ', 'អង្គារ', 'ពុធ', 'ព្រហស្បតិ៍', 'សុក្រ', 'សៅរ៍'];

async function renderCalendar() {
    const grid = document.getElementById('calendar-grid');
    const title = document.getElementById('cal-title');
    const year = calendarCursor.getFullYear();
    const month = calendarCursor.getMonth() + 1;
    title.textContent = `${KM_MONTHS[month - 1]} ${year}`;
    grid.innerHTML = `<div class="text-muted small" style="grid-column: span 7; text-align:center; padding:1rem;">កំពុងផ្ទុក...</div>`;

    let data = { days: {}, expiry: {} };
    try {
        const res = await fetch(`/api/transactions/calendar?year=${year}&month=${month}`);
        if (res.ok) data = await res.json();
    } catch (err) {
        console.error('Calendar fetch error:', err);
    }

    const first = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const startDow = first.getDay();
    const today = todayISO();

    let html = KM_DAYS.map(d => `<div class="cal-head">${d}</div>`).join('');
    for (let i = 0; i < startDow; i++) html += `<div class="cal-day empty"></div>`;
    for (let d = 1; d <= daysInMonth; d++) {
        const iso = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
        const tx = data.days[iso];
        const exp = data.expiry[iso];
        const cls = ['cal-day'];
        if (iso === today) cls.push('today');
        if (exp) cls.push('has-expiry');
        let body = '';
        if (tx && tx.in_qty) body += `<span class="cal-in">📥 +${tx.in_qty} <small>(${tx.in_count})</small></span>`;
        if (tx && tx.out_qty) body += `<span class="cal-out">📤 -${tx.out_qty} <small>(${tx.out_count})</small></span>`;
        if (exp) body += `<span class="cal-exp" title="${escapeHtml(exp.names || '')}">⏰ ${exp.batches} ឡូតិ៍ / ${exp.qty}</span>`;
        html += `<div class="${cls.join(' ')}" onclick="showTransactionsForDay('${iso}')" title="មើលប្រតិបត្តិការថ្ងៃ ${iso}"><span class="cal-num">${d}</span>${body}</div>`;
    }
    grid.innerHTML = html;
}

document.getElementById('cal-prev').addEventListener('click', () => { calendarCursor = new Date(calendarCursor.getFullYear(), calendarCursor.getMonth() - 1, 1); renderCalendar(); });
document.getElementById('cal-next').addEventListener('click', () => { calendarCursor = new Date(calendarCursor.getFullYear(), calendarCursor.getMonth() + 1, 1); renderCalendar(); });
document.getElementById('cal-today').addEventListener('click', () => { calendarCursor = new Date(); renderCalendar(); });

// ==========================================
// Expiry Tab
// ==========================================
async function fetchExpiry() {
    const status = document.getElementById('expiry-status-filter').value;
    const days = document.getElementById('expiry-days-filter').value;
    const search = document.getElementById('expiry-search').value.trim();
    const body = document.getElementById('expiry-table-body');
    const params = new URLSearchParams({ status, days });
    if (search) params.set('search', search);
    try {
        const res = await fetch(`/api/expiry?${params.toString()}`);
        if (!res.ok) throw new Error('Failed to fetch expiry');
        const data = await res.json();
        expiryBatchesCache = data.batches;
        document.getElementById('exp-sum-expired-b').textContent = data.summary.expired.batches;
        document.getElementById('exp-sum-expired-q').textContent = data.summary.expired.qty;
        document.getElementById('exp-sum-soon-b').textContent = data.summary.expiring_soon.batches;
        document.getElementById('exp-sum-soon-q').textContent = data.summary.expiring_soon.qty;
        renderExpiryTable(data.batches);
    } catch (err) {
        console.error(err);
        body.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-danger">❌ មានបញ្ហាក្នុងការទាញយកទិន្នន័យ!</td></tr>`;
    }
}

function renderExpiryTable(batches) {
    const body = document.getElementById('expiry-table-body');
    const isAdmin = currentUser && currentUser.role === 'admin';
    if (!batches.length) {
        body.innerHTML = `<tr><td colspan="8" class="text-center py-5 text-muted">✅ មិនមានឡូតិ៍ត្រូវនឹងតម្រងនេះទេ។</td></tr>`;
        return;
    }
    body.innerHTML = batches.map(b => {
        const days = daysUntil(b.expiry_date);
        let left;
        if (days < 0) left = `<span class="badge badge-danger">ផុតកំណត់ ${Math.abs(days)} ថ្ងៃហើយ</span>`;
        else if (days === 0) left = `<span class="badge badge-danger">ផុតកំណត់ថ្ងៃនេះ</span>`;
        else if (days <= EXPIRY_WARN_DAYS) left = `<span class="badge badge-warning">${days} ថ្ងៃទៀត</span>`;
        else left = `<span class="badge badge-success">${days} ថ្ងៃទៀត</span>`;
        const discardBtn = isAdmin ? `<button class="btn btn-danger btn-sm" onclick="discardBatch(${b.id}, '${b.expiry_date}', ${b.quantity})" title="បោះចោលឡូតិ៍ (កាត់ស្តុក)">🗑️ បោះចោល</button>` : '';
        return `
            <tr>
                <td>${b.batch_no ? `<span class="badge badge-code">${escapeHtml(b.batch_no)}</span>` : '<span class="text-muted">—</span>'}</td>
                <td><strong>${b.expiry_date}</strong></td>
                <td>${left}</td>
                <td><strong>${escapeHtml(b.product_name)}</strong> <small class="text-muted">(${escapeHtml(b.product_code)})</small></td>
                <td><span class="badge badge-info">${escapeHtml(b.product_category || 'ទូទៅ')}</span></td>
                <td><strong>${b.quantity}</strong> <small class="text-muted">${escapeHtml(b.product_unit || '')}</small></td>
                <td>${escapeHtml(b.product_location || '')}</td>
                <td>
                    <div class="actions-cell">
                        <button class="btn btn-warning btn-sm" onclick="openStockOutModal(${b.product_id}, ${b.id})">📤 ដកចេញ</button>
                        <button class="btn btn-secondary btn-sm" onclick="openBatchesModal(${b.product_id})">⏰</button>
                        ${discardBtn}
                    </div>
                </td>
            </tr>`;
    }).join('');
}

document.getElementById('expiry-status-filter').addEventListener('change', fetchExpiry);
document.getElementById('expiry-days-filter').addEventListener('change', fetchExpiry);
let expSearchTimer = null;
document.getElementById('expiry-search').addEventListener('input', () => { clearTimeout(expSearchTimer); expSearchTimer = setTimeout(fetchExpiry, 350); });
document.getElementById('btn-refresh-expiry').addEventListener('click', () => { fetchExpiry(); showToast('🔄 បានផ្ទុកទិន្នន័យផុតកំណត់ថ្មី'); });

window.discardBatch = async function(batchId, expiry, qty) {
    if (!confirm(`បោះចោលឡូតិ៍ផុតកំណត់ ${expiry} (ចំនួន ${qty})?\nស្តុកសរុបរបស់ទំនិញនឹងត្រូវកាត់ ${qty} ដែរ។`)) return;
    try {
        const res = await fetch(`/api/batches/${batchId}?reason=${encodeURIComponent('បោះចោលទំនិញផុតកំណត់')}`, { method: 'DELETE' });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');
        showToast(result.message);
        fetchStats(); fetchProducts(); fetchExpiry();
        if (document.getElementById('modal-batches').classList.contains('show')) {
            loadBatchesTable(parseInt(document.getElementById('batch-add-product-id').value), 'modal');
        }
        if (document.getElementById('modal-edit-product').classList.contains('show') && editBatchesProductId) {
            loadBatchesTable(editBatchesProductId, 'edit');
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
};

// ==========================================
// Batches (per product) — shared by Batches modal & Edit modal
// ctx = 'modal' (modal-batches) | 'edit' (inside edit-product modal)
// ==========================================
const BATCH_CTX = {
    modal: { body: 'batches-table-body', note: 'batches-untracked-note', title: 'batches-product-title', summary: null },
    edit:  { body: 'edit-batches-body',  note: 'edit-batches-note',      title: null,                    summary: 'edit-batches-summary' }
};

async function loadBatchesTable(productId, ctx) {
    const cfg = BATCH_CTX[ctx];
    const body = document.getElementById(cfg.body);
    const isAdmin = currentUser && currentUser.role === 'admin';
    body.innerHTML = `<tr><td colspan="5" class="text-center text-muted">កំពុងផ្ទុក...</td></tr>`;
    try {
        const res = await fetch(`/api/products/${productId}/batches`);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();
        if (cfg.title) {
            document.getElementById(cfg.title).textContent =
                `ទំនិញ៖ ${data.product.name} (${data.product.code}) — ស្តុកសរុប ${data.product.quantity} ${data.product.unit}`;
        }
        if (cfg.summary) {
            document.getElementById(cfg.summary).textContent =
                `${data.batches.length} ឡូតិ៍ · តាមដាន ${data.tracked_qty}/${data.product.quantity} ${data.product.unit}`;
        }
        document.getElementById(cfg.note).textContent = data.untracked_qty > 0
            ? `ℹ️ មាន ${data.untracked_qty} ${data.product.unit} ដែលមិនមានលេខឡូតិ៍/ថ្ងៃផុតកំណត់ (ស្តុកចាស់ ឬនាំចូលដោយមិនបញ្ចូល)។`
            : '';
        if (!data.batches.length) {
            body.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-5">📭 មិនទាន់មានឡូតិ៍ទេ — បន្ថែមខាងក្រោម។</td></tr>`;
            return;
        }
        const pfx = ctx === 'edit' ? 'e' : 'm';
        body.innerHTML = data.batches.map(b => {
            const qtyCell = isAdmin
                ? `<input type="number" class="batch-edit-input" style="width:76px" value="${b.quantity}" min="0" id="${pfx}bq-${b.id}">`
                : `<strong>${b.quantity}</strong>`;
            const discard = isAdmin ? `<button class="btn btn-danger btn-sm" onclick="discardBatch(${b.id}, '${b.expiry_date}', ${b.quantity})" title="បោះចោលឡូតិ៍">🗑️</button>` : '';
            const closeFirst = ctx === 'edit' ? "closeModal('modal-edit-product');" : "closeModal('modal-batches');";
            return `
                <tr>
                    <td><input type="text" class="batch-edit-input" style="width:110px" value="${escapeHtml(b.batch_no || '')}" placeholder="—" id="${pfx}bn-${b.id}"></td>
                    <td><input type="date" class="batch-edit-input" value="${b.expiry_date}" id="${pfx}bd-${b.id}"></td>
                    <td>${daysLeftBadge(b.expiry_date)}</td>
                    <td>${qtyCell}</td>
                    <td>
                        <div class="actions-cell">
                            <button type="button" class="btn btn-primary btn-sm" onclick="saveBatch(${b.id}, ${isAdmin}, '${ctx}')" title="រក្សាទុក">💾</button>
                            <button type="button" class="btn btn-warning btn-sm" onclick="${closeFirst} openStockOutModal(${productId}, ${b.id})" title="ដកចេញពីឡូតិ៍នេះ">📤</button>
                            ${discard}
                        </div>
                    </td>
                </tr>`;
        }).join('');
    } catch (err) {
        body.innerHTML = `<tr><td colspan="5" class="text-center text-danger">❌ បរាជ័យក្នុងការទាញយកឡូតិ៍</td></tr>`;
    }
}

window.openBatchesModal = function(productId) {
    document.getElementById('batch-add-product-id').value = productId;
    document.getElementById('batch-add-no').value = '';
    document.getElementById('batch-add-expiry').value = '';
    document.getElementById('batch-add-qty').value = 1;
    openModal('modal-batches');
    loadBatchesTable(productId, 'modal');
};

window.saveBatch = async function(batchId, isAdmin, ctx) {
    const pfx = ctx === 'edit' ? 'e' : 'm';
    const payload = {
        expiry_date: document.getElementById(`${pfx}bd-${batchId}`).value,
        batch_no: document.getElementById(`${pfx}bn-${batchId}`).value.trim()
    };
    if (isAdmin) {
        const q = document.getElementById(`${pfx}bq-${batchId}`);
        if (q) payload.quantity = parseInt(q.value);
    }
    try {
        const res = await fetch(`/api/batches/${batchId}`, {
            method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');
        showToast(result.message);
        const pid = ctx === 'edit' ? editBatchesProductId : parseInt(document.getElementById('batch-add-product-id').value);
        fetchStats(); fetchProducts(); loadBatchesTable(pid, ctx);
        if (document.getElementById('tab-expiry').classList.contains('active')) fetchExpiry();
    } catch (err) {
        showToast(err.message, 'error');
    }
};

async function addBatchStockIn(productId, batchNo, expiry, qty, ctx) {
    if (!expiry) { showToast('សូមបញ្ចូលថ្ងៃផុតកំណត់!', 'error'); return; }
    if (!qty || qty < 1) { showToast('ចំនួនត្រូវតែធំជាង ០!', 'error'); return; }
    const data = {
        product_id: productId,
        quantity: qty,
        unit_price: 0,
        reference: 'បន្ថែមឡូតិ៍តាម Web',
        expiry_date: expiry,
        batch_no: (batchNo || '').trim() || null
    };
    try {
        const res = await fetch('/api/stock-in', {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'បរាជ័យ');
        showToast(`📥 បានបន្ថែមឡូតិ៍ ${data.batch_no ? data.batch_no + ' · ' : ''}${expiry} (+${qty})`);
        fetchStats(); fetchProducts(); fetchTransactions();
        loadBatchesTable(productId, ctx);
        if (ctx === 'edit') {
            document.getElementById('edit-batch-no').value = '';
            document.getElementById('edit-batch-expiry').value = '';
            document.getElementById('edit-batch-qty').value = 1;
        } else {
            document.getElementById('batch-add-no').value = '';
            document.getElementById('batch-add-expiry').value = '';
            document.getElementById('batch-add-qty').value = 1;
        }
    } catch (err) {
        showToast(err.message, 'error');
    }
}

document.getElementById('form-add-batch').addEventListener('submit', (e) => {
    e.preventDefault();
    addBatchStockIn(
        parseInt(document.getElementById('batch-add-product-id').value),
        document.getElementById('batch-add-no').value,
        document.getElementById('batch-add-expiry').value,
        parseInt(document.getElementById('batch-add-qty').value),
        'modal'
    );
});

// ==========================================
// Import Modal (CSV / Excel)
// ==========================================
document.getElementById('btn-open-import-modal').addEventListener('click', () => {
    document.getElementById('form-import').reset();
    document.getElementById('import-update-existing').checked = true;
    document.getElementById('import-preview').style.display = 'none';
    document.getElementById('import-result').style.display = 'none';
    openModal('modal-import');
});

async function submitImport(dryRun) {
    const fileInput = document.getElementById('import-file');
    if (!fileInput.files.length) { showToast('សូមជ្រើសរើសឯកសារ CSV ឬ Excel ជាមុន!', 'error'); return; }
    const fd = new FormData();
    fd.append('file', fileInput.files[0]);
    fd.append('update_existing', document.getElementById('import-update-existing').checked ? 'true' : 'false');
    fd.append('dry_run', dryRun ? 'true' : 'false');

    const btnPrev = document.getElementById('btn-import-preview');
    const btnSub = document.getElementById('btn-import-submit');
    btnPrev.disabled = btnSub.disabled = true;
    const previewBox = document.getElementById('import-preview');
    const resultBox = document.getElementById('import-result');
    try {
        const res = await fetch('/api/import/products', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'បរាជ័យ');

        if (dryRun) {
            const cols = data.columns;
            const rows = data.preview;
            previewBox.style.display = 'block';
            resultBox.style.display = 'none';
            previewBox.innerHTML = `
                <strong>👁️ មើលជាមុន — សរុប ${data.total} ជួរ</strong> <span class="text-muted">(បង្ហាញ ${rows.length} ជួរដំបូង; column ដែលស្គាល់៖ ${cols.join(', ')})</span>
                <div class="table-responsive" style="margin-top:0.5rem;">
                <table><thead><tr>${cols.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead>
                <tbody>${rows.map(r => `<tr>${cols.map(c => `<td>${escapeHtml(r[c] ?? '')}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
        } else {
            previewBox.style.display = 'none';
            resultBox.style.display = 'block';
            const errs = data.errors || [];
            resultBox.innerHTML = `
                <strong>✅ នាំចូលរួចរាល់៖ ${data.success}/${data.total} ជួរ</strong>
                <ul>
                    <li>🆕 បង្កើតទំនិញថ្មី៖ <strong>${data.created}</strong></li>
                    <li>✏️ កែទំនិញមានស្រាប់៖ <strong>${data.updated}</strong> ${data.skipped ? `(រំលង ${data.skipped})` : ''}</li>
                    <li>📥 ស្តុកបន្ថែមសរុប៖ <strong>${data.stock_added}</strong> ឯកតា — ⏰ ឡូតិ៍ផុតកំណត់៖ <strong>${data.batches}</strong></li>
                </ul>
                ${errs.length ? `<p class="err" style="margin-top:0.5rem;"><strong>⚠️ ជួរដែលមានបញ្ហា (${errs.length}):</strong></p><ul>${errs.map(e => `<li class="err">ជួរ ${e.row} (${escapeHtml(e.code || '-')}): ${escapeHtml(e.error)}</li>`).join('')}</ul>` : ''}`;
            showToast(`📤 Import រួចរាល់៖ បង្កើត ${data.created}, កែ ${data.updated}, ឡូតិ៍ ${data.batches}`);
            fetchStats(); fetchProducts(); fetchTransactions();
        }
    } catch (err) {
        showToast(err.message, 'error');
    } finally {
        btnPrev.disabled = btnSub.disabled = false;
    }
}

document.getElementById('btn-import-preview').addEventListener('click', () => submitImport(true));
document.getElementById('form-import').addEventListener('submit', (e) => { e.preventDefault(); submitImport(false); });

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

// ស្ថានភាព Telegram Bot លើ navbar pill (Local mode = គ្មាន Bot) — មិនរារាំង boot ទេ
async function updateSystemStatusPill() {
    try {
        const pillText = document.getElementById('status-pill-text');
        if (!pillText) return;
        const res = await fetch('/api/system/status');
        if (!res.ok) return;
        const data = await res.json();
        pillText.textContent = data.telegram_bot
            ? '🤖 Telegram Bot: សកម្ម'
            : '💻 Local Mode (គ្មាន Bot)';
    } catch (e) {
        // មិនអីទេ — រក្សាអត្ថបទលំនាំដើម
    }
}

// Initial boot
(async () => {
    const isOk = await checkAuth();
    if (isOk) {
        updateSystemStatusPill();
        fetchStats();
        fetchProducts();
    }
})();
