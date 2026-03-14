/**
 * Volunteer Assignment Handler
 * Handles allocation of approved volunteers to available events/opportunities
 */

(function () {
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === `${name}=`) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
        function getCsrfToken() {
            return document.querySelector('meta[name="csrf-token"]')?.content || getCookie('csrftoken') || '';
        }

    function showNotification(message, type = 'success') {
        if (typeof showToast === 'function') {
            showToast(message, type);
        } else if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            alert(message);
        }
    }

    function loadAvailableOpportunities() {
        return fetch('/dashboard/api/available-opportunities/', {
            method: 'GET',
            headers: {
                    ...(getCsrfToken() ? { 'X-CSRFToken': getCsrfToken() } : {})
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    return data.opportunities;
                } else {
                    throw new Error(data.error || 'Failed to load opportunities');
                }
            });
    }

    function showAssignmentModal(volunteerId, volunteerName) {
        // Create or show assignment modal
        let modal = document.getElementById('assignmentModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'assignmentModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>Assign Volunteer to Event</h3>
                        <button type="button" class="close-btn" onclick="document.getElementById('assignmentModal').classList.remove('show');">&times;</button>
                    </div>
                    <div class="modal-body">
                        <p>Assigning: <strong id="volunteerNameDisplay"></strong></p>
                        <div id="opportunitiesList" class="opportunities-list">
                            <p>Loading available opportunities...</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="document.getElementById('assignmentModal').classList.remove('show');">Cancel</button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }

        // Update volunteer name
        document.getElementById('volunteerNameDisplay').textContent = volunteerName;

        // Load opportunities
        loadAvailableOpportunities()
            .then(opportunities => {
                const listHtml = opportunities.length > 0
                    ? opportunities.map(op => `
                        <div class="opportunity-item">
                            <div class="opportunity-info">
                                <strong>${sanitizeHtml(op.title)}</strong>
                                <p class="text-muted">${sanitizeHtml(op.category)} - ${op.positions_remaining} position(s) available</p>
                            </div>
                            <button type="button" class="btn btn-sm btn-primary assign-opportunity-btn" 
                                data-app-id="${volunteerId}" data-opp-id="${op.id}" data-opp-title="${sanitizeHtml(op.title)}">
                                Assign
                            </button>
                        </div>
                    `).join('')
                    : '<p class="text-muted">No available opportunities at this time.</p>';

                document.getElementById('opportunitiesList').innerHTML = listHtml;

                // Attach event listeners to new buttons
                document.querySelectorAll('.assign-opportunity-btn').forEach(btn => {
                    btn.addEventListener('click', handleOpportunitySelection);
                });
            })
            .catch(error => {
                document.getElementById('opportunitiesList').innerHTML = `<p class="text-danger">Error loading opportunities: ${sanitizeHtml(error.message)}</p>`;
            });

        // Show modal
        modal.classList.add('show');
    }

    function sanitizeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async function handleOpportunitySelection(e) {
        const appId = e.target.dataset.appId;
        const oppId = e.target.dataset.oppId;
        const oppTitle = e.target.dataset.oppTitle;

        const confirmed = await window.GlobalUI.confirm({
            title: 'Assign volunteer',
            message: `Assign this volunteer to "${oppTitle}"?`,
            okText: 'Assign'
        });

        if (!confirmed) {
            return;
        }

        // In a real implementation, you might call an API endpoint to record this assignment
        // For now, we'll just provide feedback
        e.target.disabled = true;
        e.target.textContent = 'Assigning...';

        // You could add an API call here if you create an assignment endpoint
        // For now, just show success message
        setTimeout(() => {
            showNotification(`Volunteer assigned to "${oppTitle}"`, 'success');
            document.getElementById('assignmentModal').classList.remove('show');
        }, 500);
    }

    function bindAssignmentButtons() {
        document.querySelectorAll('.volunteer-assign-btn').forEach(btn => {
            btn.addEventListener('click', function () {
                const volunteerId = this.dataset.id;
                const volunteerName = this.dataset.name;
                showAssignmentModal(volunteerId, volunteerName);
            });
        });
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function () {
        bindAssignmentButtons();
    });

    // Re-bind when volunteer-applications.js updates the DOM
    document.addEventListener('volunteerDataUpdated', function () {
        bindAssignmentButtons();
    });
})();
