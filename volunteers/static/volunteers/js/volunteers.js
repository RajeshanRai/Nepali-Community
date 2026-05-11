/**
 * Volunteers JavaScript
 * Handles volunteer opportunity interactions and applications
 */

(function () {
    'use strict';

    /**
     * Get CSRF token from cookies
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    const csrftoken = getCookie('csrftoken');

    /**
     * Initialize volunteers page functionality
     */
    function init() {
        initApplicationForm();
        initFilterAnimations();
        initCardAnimations();
    }

    /**
     * Initialize volunteer application form
     */
    function initApplicationForm() {
        const applicationForms = document.querySelectorAll('.volunteer-application-form');

        applicationForms.forEach(form => {
            form.addEventListener('submit', async function (e) {
                e.preventDefault();

                const submitButton = form.querySelector('button[type="submit"]');
                const originalText = submitButton.innerHTML;

                // Show loading state
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Submitting...';

                const formData = new FormData(form);
                const opportunityId = form.getAttribute('data-opportunity-id');

                try {
                    const response = await fetch(form.action, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': csrftoken
                        }
                    });

                    if (response.ok) {
                        const data = await response.json();

                        if (data.success) {
                            showNotification('Application submitted successfully!', 'success');

                            // Clear form
                            form.reset();

                            // Show success message
                            setTimeout(() => {
                                const successMessage = document.createElement('div');
                                successMessage.className = 'success-banner';
                                successMessage.innerHTML =
                                    '<i class="fas fa-check-circle"></i>' +
                                    '<div>' +
                                    '<h4>Application Submitted!</h4>' +
                                    '<p>We\'ll review your application and contact you soon.</p>' +
                                    '</div>';

                                form.parentElement.insertBefore(successMessage, form);
                                form.style.display = 'none';
                            }, 500);

                        } else {
                            showNotification(data.message || 'Failed to submit application', 'error');
                        }
                    } else {
                        showNotification('Failed to submit application. Please try again.', 'error');
                    }
                } catch (error) {
                    console.error('Application error:', error);
                    showNotification('An error occurred. Please try again.', 'error');
                } finally {
                    // Reset button
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }
            });
        });
    }

    /**
     * Initialize filter button animations
     */
    function initFilterAnimations() {
        const filterButtons = document.querySelectorAll('.filter-btn');

        filterButtons.forEach(btn => {
            btn.addEventListener('click', function (e) {
                // Add click animation
                this.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    this.style.transform = 'scale(1)';
                }, 150);
            });
        });
    }

    /**
     * Initialize card hover animations
     */
    function initCardAnimations() {
        const cards = document.querySelectorAll('.opportunity-card');

        cards.forEach(card => {
            card.addEventListener('mouseenter', function () {
                this.style.transform = 'translateY(-8px)';
            });

            card.addEventListener('mouseleave', function () {
                this.style.transform = 'translateY(0)';
            });
        });
    }

    /**
     * Show notification
     */
    function showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;

        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };

        const colors = {
            success: '#4caf50',
            error: '#f44336',
            warning: '#ff9800',
            info: '#2196f3'
        };

        notification.style.cssText =
            'position: fixed;' +
            'top: 2rem;' +
            'right: 2rem;' +
            'background: ' + (colors[type] || colors.info) + ';' +
            'color: white;' +
            'padding: 1rem 1.5rem;' +
            'border-radius: 12px;' +
            'box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);' +
            'z-index: 10000;' +
            'display: flex;' +
            'align-items: center;' +
            'gap: 0.75rem;' +
            'font-weight: 500;' +
            'animation: slideInRight 0.3s ease;' +
            'max-width: 400px;';

        notification.innerHTML =
            '<i class="fas fa-' + (icons[type] || icons.info) + '" style="font-size: 1.25rem;"></i>' +
            '<span>' + message + '</span>';

        document.body.appendChild(notification);

        // Auto remove
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => {
                if (document.body.contains(notification)) {
                    document.body.removeChild(notification);
                }
            }, 300);
        }, 4000);
    }

    /**
     * Generate skeleton loader for opportunities grid
     */
    function generateSkeleton(count = 6) {
        const grid = document.querySelector('.opportunities-grid');
        if (!grid) return;

        grid.innerHTML = '';

        for (let i = 0; i < count; i++) {
            const skeleton = document.createElement('div');
            skeleton.className = 'opportunity-card skeleton-card';
            skeleton.innerHTML =
                '<div class="card-header">' +
                '<div class="skeleton skeleton-badge" style="width: 120px; height: 28px;"></div>' +
                '</div>' +
                '<div class="skeleton skeleton-title" style="width: 80%; height: 28px; margin-bottom: 1rem;"></div>' +
                '<div class="skeleton skeleton-text" style="width: 100%; height: 60px; margin-bottom: 1rem;"></div>' +
                '<div class="skeleton skeleton-text" style="width: 60%; height: 20px; margin-bottom: 0.5rem;"></div>' +
                '<div class="skeleton skeleton-text" style="width: 70%; height: 20px; margin-bottom: 0.5rem;"></div>' +
                '<div class="skeleton skeleton-text" style="width: 50%; height: 20px; margin-bottom: 1.5rem;"></div>' +
                '<div class="skeleton skeleton-button" style="width: 100%; height: 44px;"></div>';
            grid.appendChild(skeleton);
        }
    }

    /**
     * Initialize on DOM ready
     */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Add animation styles
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(100%);
                opacity: 0;
            }
        }
        
        .skeleton {
            background: linear-gradient(
                90deg,
                rgba(26, 26, 26, 0.08) 25%,
                rgba(26, 26, 26, 0.12) 50%,
                rgba(26, 26, 26, 0.08) 75%
            );
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 8px;
        }
        
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        
        .success-banner {
            background: linear-gradient(135deg, #4caf50, #45a049);
            color: white;
            padding: 2rem;
            border-radius: 16px;
            display: flex;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(76, 175, 80, 0.3);
            animation: slideInUp 0.5s ease;
        }
        
        .success-banner i {
            font-size: 3rem;
            opacity: 0.9;
        }
        
        .success-banner h4 {
            margin: 0 0 0.5rem 0;
            font-size: 1.5rem;
        }
        
        .success-banner p {
            margin: 0;
            opacity: 0.95;
        }
        
        @keyframes slideInUp {
            from {
                transform: translateY(20px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .opportunity-card {
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .filter-btn {
            transition: transform 0.15s ease;
        }
    `;
    document.head.appendChild(style);

    // Export for potential external use
    window.VolunteersJS = {
        showNotification,
        generateSkeleton
    };

})();
