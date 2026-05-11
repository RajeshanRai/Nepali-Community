// Mobile Menu Toggle for Main Navbar
(function () {
    'use strict';

    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const mobileMenuClose = document.getElementById('mobileMenuClose');
    const mobileMenuOverlay = document.getElementById('mobileMenuOverlay');
    const navMenu = document.getElementById('navMenu');
    const dropdowns = document.querySelectorAll('.main-navbar .dropdown');

    if (!mobileMenuToggle || !navMenu || !mobileMenuOverlay) return;

    // Function to open sidebar
    function openSidebar() {
        navMenu.classList.add('open');
        mobileMenuOverlay.classList.add('active');
        mobileMenuToggle.classList.add('hamburger-hidden');
        mobileMenuToggle.setAttribute('aria-expanded', 'true');
        navMenu.setAttribute('aria-hidden', 'false');
        document.body.classList.add('mobile-menu-open');
        document.body.style.overflow = 'hidden';

        const firstLink = navMenu.querySelector('a, button');
        if (firstLink) {
            window.setTimeout(() => firstLink.focus(), 50);
        }
    }

    // Function to close sidebar
    function closeSidebar() {
        navMenu.classList.remove('open');
        mobileMenuOverlay.classList.remove('active');
        mobileMenuToggle.classList.remove('hamburger-hidden');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
        navMenu.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('mobile-menu-open');
        document.body.style.overflow = '';

        // Close all dropdowns
        dropdowns.forEach(dd => {
            dd.classList.remove('active');
            const trigger = dd.querySelector(':scope > a');
            if (trigger) {
                trigger.setAttribute('aria-expanded', 'false');
            }
        });

        mobileMenuToggle.focus();
    }

    // Toggle mobile menu
    mobileMenuToggle.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();

        if (navMenu.classList.contains('open')) {
            closeSidebar();
        } else {
            openSidebar();
        }
    });

    // Close button click
    if (mobileMenuClose) {
        mobileMenuClose.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            closeSidebar();
        });
    }

    // Close menu when clicking overlay
    mobileMenuOverlay.addEventListener('click', function () {
        closeSidebar();
    });

    // Close menu on Escape key
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && navMenu.classList.contains('open')) {
            closeSidebar();
        }
    });

    // Handle dropdown toggles on mobile
    dropdowns.forEach(dropdown => {
        const dropdownLink = dropdown.querySelector(':scope > a');

        if (!dropdownLink) return;

        dropdownLink.addEventListener('click', function (e) {
            // Only prevent default and toggle on mobile
            if (window.innerWidth <= 1024) {
                e.preventDefault();
                e.stopPropagation();

                const isActive = dropdown.classList.contains('active');

                dropdowns.forEach(dd => {
                    dd.classList.remove('active');
                    const trigger = dd.querySelector(':scope > a');
                    if (trigger) {
                        trigger.setAttribute('aria-expanded', 'false');
                    }
                });

                if (!isActive) {
                    dropdown.classList.add('active');
                    dropdownLink.setAttribute('aria-expanded', 'true');
                }
            }
        });
    });

    // Close menu when clicking on a non-dropdown link
    const navLinks = navMenu.querySelectorAll('a');
    navLinks.forEach(link => {
        link.addEventListener('click', function () {
            const isDropdownTrigger = link.matches('.dropdown > a');

            if (window.innerWidth <= 1024 && !isDropdownTrigger) {
                closeSidebar();
            }
        });
    });

    // Handle window resize
    window.addEventListener('resize', function () {
        if (window.innerWidth > 1024) {
            closeSidebar();
        }
    });

    // Set active navigation state based on current URL
    function setActiveNav() {
        const currentPath = window.location.pathname;
        const navLinks = navMenu.querySelectorAll('a[href]');

        navLinks.forEach(link => {
            const href = link.getAttribute('href');

            // Skip external links and anchors
            if (!href || href.startsWith('#') || href.startsWith('http')) return;

            // Check if current path matches link href
            if (currentPath === href || currentPath.startsWith(href + '/')) {
                link.classList.add('active');

                // If link is inside dropdown, keep dropdown expanded on mobile
                const parentDropdown = link.closest('.dropdown');
                if (parentDropdown && window.innerWidth <= 1024) {
                    parentDropdown.classList.add('active');
                    const trigger = parentDropdown.querySelector(':scope > a');
                    if (trigger) {
                        trigger.setAttribute('aria-expanded', 'true');
                    }
                }
            } else {
                link.classList.remove('active');
            }
        });
    }

    // Set active state on page load
    setActiveNav();

    // Update active state if using client-side navigation
    window.addEventListener('popstate', setActiveNav);
})();
