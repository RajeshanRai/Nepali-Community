// ================================================
// ADMIN PANEL JAVASCRIPT
// Handles tabs, filters, and AJAX operations
// ================================================

document.addEventListener('DOMContentLoaded', function () {
    initTabSwitching();
    initSubTabSwitching();
    initFiltering();
    initApproveRejectHandlers();
});

// ===== TAB SWITCHING =====
function initTabSwitching() {
    const tabButtons = document.querySelectorAll('.admin-tabs .tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const tabName = this.dataset.tab;

            // Remove active class from all buttons and contents
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            this.classList.add('active');
            document.getElementById(`${tabName}-tab`).classList.add('active');
        });
    });
}

// ===== SUB-TAB SWITCHING =====
function initSubTabSwitching() {
    const subTabButtons = document.querySelectorAll('.sub-tab-btn');
    const subTabContents = document.querySelectorAll('.sub-tab-content');

    subTabButtons.forEach(button => {
        button.addEventListener('click', function () {
            const subTabName = this.dataset.subtab;

            // Remove active class from all buttons in parent container
            const parentVolunteerTabs = this.closest('.volunteer-tabs');
            const siblingButtons = parentVolunteerTabs.querySelectorAll('.sub-tab-btn');
            siblingButtons.forEach(btn => btn.classList.remove('active'));

            // Remove active class from all contents in parent tab
            const parentTab = this.closest('.tab-content');
            const siblingContents = parentTab.querySelectorAll('.sub-tab-content');
            siblingContents.forEach(content => content.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            this.classList.add('active');
            parentTab.querySelector(`#${subTabName}-subtab`).classList.add('active');
        });
    });
}

// ===== FILTERING =====
function initFiltering() {
    const filterButtons = document.querySelectorAll('.filter-btn');

    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            const filterValue = this.dataset.filter;
            const parentContainer = this.closest('.tab-content');
            const dataTable = parentContainer.querySelector('.data-table');

            // Update active button
            const siblingButtons = this.parentElement.querySelectorAll('.filter-btn');
            siblingButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');

            // Filter table rows
            const rows = dataTable.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const status = row.dataset.status;

                if (filterValue === 'all') {
                    row.style.display = '';
                } else if (status === filterValue) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    });
}

// ===== APPROVE/REJECT HANDLERS =====
function initApproveRejectHandlers() {
    const approveButtons = document.querySelectorAll('.btn-approve');
    const rejectButtons = document.querySelectorAll('.btn-reject');

    approveButtons.forEach(button => {
        button.addEventListener('click', handleApprove);
    });

    rejectButtons.forEach(button => {
        button.addEventListener('click', handleReject);
    });
}

async function handleApprove(e) {
    e.preventDefault();
    const btn = e.currentTarget;
    const id = btn.dataset.id;
    const kind = btn.dataset.kind || 'application';

    const approved = await window.GlobalUI.confirm({
        title: 'Approve request',
        message: 'Are you sure you want to approve this?',
        okText: 'Approve'
    });

    if (!approved) return;

    const url = getApprovalUrl(id, 'approve', kind);
    if (!url) return;

    fetchAction(url, id, btn);
}

async function handleReject(e) {
    e.preventDefault();
    const btn = e.currentTarget;
    const id = btn.dataset.id;
    const kind = btn.dataset.kind || 'application';

    const rejected = await window.GlobalUI.confirm({
        title: 'Reject request',
        message: 'Are you sure you want to reject this?',
        okText: 'Reject',
        variant: 'danger'
    });

    if (!rejected) return;

    const url = getApprovalUrl(id, 'reject', kind);
    if (!url) return;

    fetchAction(url, id, btn);
}

function getApprovalUrl(id, action, kind = 'application') {
    const currentTab = document.querySelector('.tab-content.active');
    const tabId = currentTab.id;

    // Event Requests Tab
    if (tabId === 'requests-tab') {
        return `/dashboard/requests/${id}/${action}/`;
    }

    // Volunteer Applications Tab
    if (tabId === 'volunteers-tab') {
        if (kind === 'request') {
            return `/dashboard/volunteers/requests/${id}/${action}/`;
        }
        return `/dashboard/volunteers/applications/${id}/${action}/`;
    }

    return null;
}

function fetchAction(url, id, button) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || getCookie('csrftoken') || '';
    const formData = new FormData();
    if (csrfToken) {
        formData.append('csrfmiddlewaretoken', csrfToken);
    }

    fetch(url, {
        method: 'POST',
        body: formData,
        headers: {
            ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
        }
    })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(data.message, 'success');
                // Update row status
                const row = button.closest('tr');
                const statusCell = row.querySelector('td:nth-child(4)');

                if (button.classList.contains('btn-approve')) {
                    statusCell.innerHTML = '<span class="badge badge-success">Approved</span>';
                    // Hide action buttons
                    button.parentElement.innerHTML = '<span class="badge badge-success">Approved</span>';
                } else {
                    statusCell.innerHTML = '<span class="badge badge-danger">Rejected</span>';
                    button.parentElement.innerHTML = '<span class="badge badge-danger">Rejected</span>';
                }
            } else {
                showNotification(data.message || 'Error occurred', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
}

// ===== NOTIFICATION TOAST =====
function showNotification(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `notification notification-${type}`;
    toast.textContent = message;

    const style = document.createElement('style');
    style.innerHTML = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            color: white;
            font-weight: 600;
            z-index: 9999;
            animation: slideIn 0.3s ease;
        }
        
        .notification-success {
            background: #22C55E;
        }
        
        .notification-error {
            background: #EF4444;
        }
        
        .notification-info {
            background: #3B82F6;
        }
        
        .notification-warning {
            background: #F59E0B;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOut {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }
    `;

    if (!document.querySelector('style[notification-styles]')) {
        style.setAttribute('notification-styles', 'true');
        document.head.appendChild(style);
    }

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ===== UTILITY: GET CSRF TOKEN =====
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === name + '=') {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

console.log('Admin Panel JS loaded successfully!');
