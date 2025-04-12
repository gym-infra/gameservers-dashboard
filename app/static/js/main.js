/**
 * Game Server Dashboard - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Auto-refresh functionality
    const AUTO_REFRESH_INTERVAL = 60000; // 1 minute
    let autoRefreshEnabled = false;
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('change', function() {
            autoRefreshEnabled = this.checked;
            
            if (autoRefreshEnabled) {
                startAutoRefresh();
            }
        });
        
        function startAutoRefresh() {
            setTimeout(function() {
                if (autoRefreshEnabled) {
                    window.location.reload();
                }
            }, AUTO_REFRESH_INTERVAL);
        }
    }

    // Add animation when cards are loaded
    document.querySelectorAll('.card').forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('show');
        }, index * 100);
    });

    // Handle API errors with a toast notification
    window.showErrorToast = function(message) {
        const toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toast-container';
            container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
            document.body.appendChild(container);
        }
        
        const toastId = 'error-toast-' + Date.now();
        const toastHtml = `
            <div id="${toastId}" class="toast" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="toast-header bg-danger text-white">
                    <strong class="me-auto">Error</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
                <div class="toast-body">
                    ${message}
                </div>
            </div>
        `;
        
        document.getElementById('toast-container').innerHTML += toastHtml;
        const toastElement = document.getElementById(toastId);
        const toast = new bootstrap.Toast(toastElement);
        toast.show();
    };
});
