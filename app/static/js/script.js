document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('sidebarCollapse').addEventListener('click', function () {
        document.getElementById('sidebar').classList.toggle('active');
    });

    // Toggle sub-menu
    const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
    dropdownToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('href'));
            target.classList.toggle('collapse');
            this.setAttribute('aria-expanded', target.classList.contains('collapse') ? 'false' : 'true');
        });
    });
});
