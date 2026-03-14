/**
 * Dashboard Responsive & Interactive Utilities
 * Handles dynamic button states, modals, and responsive behavior
 * Isolated to dashboard pages only
 */

// Global dashboard utilities object
window.DashboardUI = window.DashboardUI || {};

/**
 * Button State Management
 * Handles loading, disabled, and normal states
 */
DashboardUI.ButtonManager = {
    // Set button to loading state
    setLoading(button, isLoading = true) {
        if (!button) return;
        
        const originalText = button.innerHTML;
        
        if (isLoading) {
            button.classList.add('loading');
            button.disabled = true;
            button.dataset.originalText = originalText;
            button.innerHTML = '<span class="spinner"></span> ' + (button.dataset.loadingText || 'Loading...');
        } else {
            button.classList.remove('loading');
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || originalText;
        }
    },
    
    // Enable button
    enable(button) {
        if (!button) return;
        button.disabled = false;
        button.classList.remove('loading');
    },
    
    // Disable button
    disable(button) {
        if (!button) return;
        button.disabled = true;
    },
    
    // Set multiple buttons
    setMultiple(buttons, isLoading) {
        buttons.forEach(btn => this.setLoading(btn, isLoading));
    }
};

/**
 * Modal/Popup Manager
 * Handles opening, closing, and responsive behavior
 */
DashboardUI.ModalManager = {
    // Open modal with callback
    open(modalId, onOpen = null) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        // Prevent body scroll
        document.body.classList.add('modal-open');
        document.body.style.overflow = 'hidden';
        
        // Show modal with fade effect
        if (modal.classList) {
            modal.classList.add('show');
        } else {
            modal.style.display = 'flex';
        }
        
        // Focus trap - focus first interactive element
        setTimeout(() => {
            const focusable = modal.querySelector('input, textarea, button, select, [tabindex]');
            if (focusable) focusable.focus();
        }, 100);
        
        if (typeof onOpen === 'function') onOpen();
        
        // Accessibility: announce modal to screen readers
        this.announceToScreenReader(`${modal.querySelector('h2, h3')?.textContent || 'Modal dialog'} opened`);
    },
    
    // Close modal with callback
    close(modalId, onClose = null) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        // Remove modal-open class
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        
        // Hide modal
        if (modal.classList) {
            modal.classList.remove('show');
        } else {
            modal.style.display = 'none';
        }
        
        if (typeof onClose === 'function') onClose();
        
        // Accessibility: announce modal closed
        this.announceToScreenReader('Modal dialog closed');
    },
    
    // Close on Escape key
    closeOnEscape(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && (modal.classList.contains('show') || modal.style.display === 'flex')) {
                this.close(modalId);
            }
        });
    },
    
    // Close on backdrop click
    closeOnBackdropClick(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;
        
        const backdrop = modal.querySelector('.modal-overlay, .decision-modal-backdrop, .details-modal-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', () => this.close(modalId));
        }
    },
    
    // Announce to screen readers
    announceToScreenReader(message) {
        const announcement = document.createElement('div');
        announcement.setAttribute('aria-live', 'polite');
        announcement.setAttribute('aria-atomic', 'true');
        announcement.style.position = 'absolute';
        announcement.style.left = '-10000px';
        announcement.textContent = message;
        document.body.appendChild(announcement);
        setTimeout(() => announcement.remove(), 1000);
    },
    
    // Get modal size based on screen
    getModalSize() {
        const width = window.innerWidth;
        if (width <= 480) return 'small';
        if (width <= 768) return 'medium';
        if (width <= 1024) return 'large';
        return 'xlarge';
    }
};

/**
 * Responsive Utilities
 * Handle responsive behavior and compact mode
 */
DashboardUI.ResponsiveManager = {
    // Check if compact mode is active
    isCompactMode() {
        const sidebar = document.querySelector('.sidebar');
        return sidebar ? sidebar.classList.contains('collapsed') : false;
    },
    
    // Get current breakpoint
    getCurrentBreakpoint() {
        const width = window.innerWidth;
        if (width <= 480) return 'xs';
        if (width <= 768) return 'sm';
        if (width <= 1024) return 'md';
        if (width <= 1280) return 'lg';
        return 'xl';
    },
    
    // Watch breakpoint changes
    onBreakpointChange(callback) {
        let lastBreakpoint = this.getCurrentBreakpoint();
        
        window.addEventListener('resize', () => {
            const newBreakpoint = this.getCurrentBreakpoint();
            if (newBreakpoint !== lastBreakpoint) {
                lastBreakpoint = newBreakpoint;
                callback(newBreakpoint);
            }
        });
    },
    
    // Adjust modal position for small screens
    adjustModalPositionForSmallScreens() {
        const modals = document.querySelectorAll('.modal, .decision-modal, .details-modal');
        const isMobile = window.innerWidth <= 768;
        
        modals.forEach(modal => {
            const content = modal.querySelector('.modal-content, .details-modal-content, .decision-modal-content');
            if (content && isMobile) {
                content.style.alignSelf = 'flex-end';
                content.style.marginBottom = '20px';
            } else if (content) {
                content.style.alignSelf = 'center';
                content.style.marginBottom = '0';
            }
        });
    },
    
    // Make tables scrollable on small screens
    makeTablesResponsive() {
        const tables = document.querySelectorAll('.data-table');
        tables.forEach(table => {
            if (!table.parentElement.classList.contains('table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentElement.insertBefore(wrapper, table);
                wrapper.appendChild(table);
            }
        });
    },

    // Apply consistent sticky/header and wide-table behavior across dashboard pages
    enhanceDashboardTables() {
        const tables = document.querySelectorAll('.table-responsive table, table.data-table');

        tables.forEach((table) => {
            if (!table.classList.contains('data-table')) {
                table.classList.add('data-table');
            }

            if (table.id === 'requests-table' || table.querySelectorAll('thead th').length >= 10) {
                table.classList.add('ultra-wide-table');
            }

            const wrapper = table.closest('.table-responsive');
            if (wrapper) {
                wrapper.classList.add('table-responsive-ready');
                if (table.classList.contains('ultra-wide-table')) {
                    wrapper.classList.add('table-responsive-wide');
                }
            }

            const headerCells = table.querySelectorAll('thead th');
            headerCells.forEach((th) => {
                th.style.position = 'sticky';
                th.style.top = '0';
                th.style.zIndex = '12';
            });
        });
    }
};

/**
 * Form Manager
 * Handle form validation and submission
 */
DashboardUI.FormManager = {
    // Validate form fields
    validate(formElement) {
        const inputs = formElement.querySelectorAll('input[required], textarea[required], select[required]');
        let isValid = true;
        
        inputs.forEach(input => {
            if (!input.value.trim()) {
                input.style.borderColor = '#EF4444';
                isValid = false;
            } else {
                input.style.borderColor = '';
            }
        });
        
        return isValid;
    },
    
    // Clear form
    clear(formElement) {
        formElement.reset();
        formElement.querySelectorAll('input, textarea, select').forEach(input => {
            input.style.borderColor = '';
        });
    },
    
    // Show validation errors
    showErrors(formElement, errors) {
        Object.keys(errors).forEach(fieldName => {
            const field = formElement.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.style.borderColor = '#EF4444';
                const errorMsg = document.createElement('small');
                errorMsg.style.color = '#EF4444';
                errorMsg.textContent = errors[fieldName];
                field.parentElement.appendChild(errorMsg);
            }
        });
    }
};

/**
 * Async Action Handler
 * Handle async operations with loading states
 */
DashboardUI.AsyncHandler = {
    // Execute async action
    async execute(asyncFn, options = {}) {
        const {
            button = null,
            onSuccess = null,
            onError = null,
            showToast = true,
            successMessage = 'Operation completed successfully',
            errorMessage = 'Operation failed'
        } = options;
        
        try {
            if (button) DashboardUI.ButtonManager.setLoading(button, true);
            
            const result = await asyncFn();
            
            if (button) DashboardUI.ButtonManager.setLoading(button, false);
            
            if (showToast) window.showToast(successMessage, 'success');
            if (typeof onSuccess === 'function') await onSuccess(result);
            
            return result;
        } catch (error) {
            if (button) DashboardUI.ButtonManager.setLoading(button, false);
            
            const finalErrorMessage = error.message || errorMessage;
            if (showToast) window.showToast(finalErrorMessage, 'error');
            if (typeof onError === 'function') await onError(error);
            
            console.error('Async action error:', error);
            throw error;
        }
    }
};

/**
 * Event Delegation Manager
 * Handle event delegation for dynamic elements
 */
DashboardUI.EventManager = {
    // Add delegated event listener
    delegate(selector, eventType, callback) {
        document.addEventListener(eventType, (e) => {
            if (e.target.matches(selector)) {
                callback(e);
            }
        });
    },
    
    // Add delegated event listener on parent
    delegateOn(parentSelector, childSelector, eventType, callback) {
        const parent = document.querySelector(parentSelector);
        if (!parent) return;
        
        parent.addEventListener(eventType, (e) => {
            const target = e.target.closest(childSelector);
            if (target) callback(e);
        });
    }
};

/**
 * Notification Manager
 * Toast & notification handling
 */
DashboardUI.NotificationManager = {
    // Show toast notification
    toast(message, type = 'info', duration = 3000) {
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}]:`, message);
        }
        
        // Auto-close
        if (duration > 0) {
            setTimeout(() => {
                const toast = document.querySelector('.toast:last-child');
                if (toast) toast.remove();
            }, duration);
        }
    },
    
    // Confirm action
    confirm(message, onConfirm, onCancel = null) {
        const confirmPromise = window.GlobalUI.confirm({
            title: 'Please confirm',
            message,
            okText: 'Confirm'
        });

        confirmPromise.then((confirmed) => {
            if (confirmed) {
                if (typeof onConfirm === 'function') onConfirm();
            } else if (typeof onCancel === 'function') {
                onCancel();
            }
        });
    }
};

/**
 * Initialize Dashboard UI
 * Run on page load
 */
DashboardUI.init = function() {
    // Make tables responsive
    DashboardUI.ResponsiveManager.makeTablesResponsive();
    DashboardUI.ResponsiveManager.enhanceDashboardTables();
    
    // Watch breakpoint changes
    DashboardUI.ResponsiveManager.onBreakpointChange((breakpoint) => {
        DashboardUI.ResponsiveManager.adjustModalPositionForSmallScreens();
    });
    
    // Adjust modals on window resize
    window.addEventListener('resize', () => {
        DashboardUI.ResponsiveManager.adjustModalPositionForSmallScreens();
        DashboardUI.ResponsiveManager.enhanceDashboardTables();
    });
    
    // Close modals on Escape key (all modals)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const openModals = document.querySelectorAll('.modal.show, [style*="display: flex"]');
            openModals.forEach(modal => {
                const closeBtn = modal.querySelector('.modal-close');
                if (closeBtn) closeBtn.click();
            });
        }
    });
    
    // Prevent body scroll when modal is open
    const observer = new MutationObserver(() => {
        const hasOpenModal = document.body.classList.contains('modal-open');
        document.body.style.overflow = hasOpenModal ? 'hidden' : '';
    });
    
    observer.observe(document.body, { attributes: true });
};

/**
 * Helper: Show Toast (if not already globally defined)
 */
if (!window.showToast) {
    window.showToast = function(message, type = 'info') {
        const container = document.querySelector('.toast-container');
        if (!container) return;
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-circle' : 'info-circle'}"></i>
            <span>${message}</span>
        `;
        
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    };
}

/**
 * Auto-initialize on DOM ready
 */
document.addEventListener('DOMContentLoaded', () => {
    DashboardUI.init();
});

// Export for use
window.DashboardUI = DashboardUI;
