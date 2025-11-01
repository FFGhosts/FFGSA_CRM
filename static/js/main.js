// PiCMS Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Confirm dialogs for delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            const message = this.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    });
    
    // File upload preview
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileSize = (file.size / 1024 / 1024).toFixed(2);
                console.log(`Selected file: ${file.name} (${fileSize} MB)`);
                
                // Update UI with file info if there's a display element
                const displayElement = document.getElementById(this.id + '-display');
                if (displayElement) {
                    displayElement.textContent = `${file.name} (${fileSize} MB)`;
                }
            }
        });
    });
    
    // Show loading spinner on form submissions
    const loadingForms = document.querySelectorAll('form[data-loading]');
    loadingForms.forEach(function(form) {
        form.addEventListener('submit', function() {
            showLoadingSpinner();
        });
    });
    
    // Copy to clipboard functionality
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(function() {
            showNotification('Copied to clipboard!', 'success');
        }).catch(function(err) {
            console.error('Failed to copy:', err);
            showNotification('Failed to copy', 'danger');
        });
    };
    
    // Show notification
    window.showNotification = function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.setAttribute('role', 'alert');
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(alertDiv, container.firstChild);
            
            setTimeout(function() {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }, 3000);
        }
    };
    
    // Loading spinner functions
    window.showLoadingSpinner = function() {
        let spinner = document.getElementById('loadingSpinner');
        if (!spinner) {
            spinner = document.createElement('div');
            spinner.id = 'loadingSpinner';
            spinner.className = 'spinner-overlay';
            spinner.innerHTML = `
                <div class="spinner-border text-light" role="status" style="width: 3rem; height: 3rem;">
                    <span class="visually-hidden">Loading...</span>
                </div>
            `;
            document.body.appendChild(spinner);
        }
        spinner.classList.add('show');
    };
    
    window.hideLoadingSpinner = function() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) {
            spinner.classList.remove('show');
        }
    };
    
    // Refresh device status indicators
    window.refreshDeviceStatus = function() {
        fetch('/api/health')
            .then(response => response.json())
            .then(data => {
                console.log('Server health check:', data);
            })
            .catch(error => {
                console.error('Health check failed:', error);
            });
    };
    
    // Auto-refresh device status every 30 seconds
    if (window.location.pathname.includes('/devices') || 
        window.location.pathname.includes('/dashboard')) {
        setInterval(function() {
            // Optionally reload page or update via AJAX
            // location.reload();
        }, 30000);
    }
    
    // Format file sizes
    window.formatFileSize = function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
    };
    
    // Format durations
    window.formatDuration = function(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        
        if (h > 0) {
            return `${h}h ${m}m ${s}s`;
        } else if (m > 0) {
            return `${m}m ${s}s`;
        } else {
            return `${s}s`;
        }
    };
    
    // Table sorting (optional enhancement)
    window.sortTable = function(table, column, asc = true) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aValue = a.children[column].textContent.trim();
            const bValue = b.children[column].textContent.trim();
            
            return asc 
                ? aValue.localeCompare(bValue, undefined, {numeric: true})
                : bValue.localeCompare(aValue, undefined, {numeric: true});
        });
        
        rows.forEach(row => tbody.appendChild(row));
    };
    
    // Initialize tooltips if Bootstrap tooltips are used
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers if Bootstrap popovers are used
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Phase 6: Update notification badge
    updateNotificationBadge();
    
    // Poll for new notifications every 30 seconds
    setInterval(updateNotificationBadge, 30000);
    
    // Initialize Socket.IO for real-time notifications
    if (typeof io !== 'undefined') {
        initializeSocketIO();
    }
    
    console.log('PiCMS initialized successfully');
});

// Phase 6: Socket.IO initialization for real-time notifications
function initializeSocketIO() {
    const socket = io();
    
    socket.on('connect', function() {
        console.log('WebSocket connected');
    });
    
    socket.on('notification', function(data) {
        console.log('Received notification:', data);
        
        // Update badge immediately
        updateNotificationBadge();
        
        // Show toast notification
        showToastNotification(data);
        
        // Play notification sound (optional)
        // playNotificationSound();
    });
    
    socket.on('disconnect', function() {
        console.log('WebSocket disconnected');
    });
    
    socket.on('error', function(error) {
        console.error('WebSocket error:', error);
    });
}

// Phase 6: Show toast notification
function showToastNotification(notification) {
    // Create toast container if it doesn't exist
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
        toastContainer.style.zIndex = '9999';
        document.body.appendChild(toastContainer);
    }
    
    // Determine icon and color based on type
    let iconClass = 'bi-info-circle';
    let bgClass = 'bg-primary';
    
    switch(notification.type) {
        case 'success':
            iconClass = 'bi-check-circle-fill';
            bgClass = 'bg-success';
            break;
        case 'warning':
            iconClass = 'bi-exclamation-triangle-fill';
            bgClass = 'bg-warning';
            break;
        case 'error':
            iconClass = 'bi-x-circle-fill';
            bgClass = 'bg-danger';
            break;
        case 'device_alert':
            iconClass = 'bi-cpu-fill';
            bgClass = 'bg-warning';
            break;
        case 'system_alert':
            iconClass = 'bi-exclamation-diamond-fill';
            bgClass = 'bg-danger';
            break;
    }
    
    // Use custom icon if provided
    if (notification.icon) {
        iconClass = notification.icon;
    }
    
    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    toastEl.innerHTML = `
        <div class="toast-header ${bgClass} text-white">
            <i class="${iconClass} me-2"></i>
            <strong class="me-auto">${notification.title}</strong>
            <small>Just now</small>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${notification.message}
            ${notification.action_url ? `
                <hr>
                <a href="${notification.action_url}" class="btn btn-sm btn-primary">View Details</a>
            ` : ''}
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // Show toast
    const toast = new bootstrap.Toast(toastEl, {
        autohide: notification.priority === 'urgent' ? false : true,
        delay: notification.priority === 'high' ? 10000 : 5000
    });
    toast.show();
    
    // Remove from DOM after hidden
    toastEl.addEventListener('hidden.bs.toast', function() {
        toastEl.remove();
    });
}

// Phase 6: Update notification badge with unread count
function updateNotificationBadge() {
    fetch('/api/notifications/unread')
        .then(response => response.json())
        .then(data => {
            const badge = document.getElementById('notificationBadge');
            const bell = document.getElementById('notificationBell');
            
            if (data.count > 0) {
                badge.textContent = data.count;
                badge.style.display = 'inline-block';
                bell.classList.add('text-warning');
            } else {
                badge.style.display = 'none';
                bell.classList.remove('text-warning');
            }
        })
        .catch(error => {
            console.error('Failed to fetch notifications:', error);
        });
}

// Handle page visibility changes
document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
        // Page became visible, refresh notifications
        updateNotificationBadge();
        console.log('Page visible, refreshed notifications');
    }
});

// Global error handler
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
});
