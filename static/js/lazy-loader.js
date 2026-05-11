/**
 * Lazy Loading Utility
 * Handles lazy loading of images with intersection observer
 * Provides fallback for browsers without IntersectionObserver support
 */

(function () {
    'use strict';

    /**
     * Initialize lazy loading for images
     */
    function initLazyLoading() {
        const lazyImages = document.querySelectorAll('img[loading="lazy"]');

        // Check for IntersectionObserver support
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        loadImage(img);
                        observer.unobserve(img);
                    }
                });
            }, {
                rootMargin: '50px 0px', // Start loading 50px before entering viewport
                threshold: 0.01
            });

            lazyImages.forEach(img => {
                // Add loading class for CSS transitions
                img.classList.add('lazy-image');
                imageObserver.observe(img);
            });
        } else {
            // Fallback for browsers without IntersectionObserver
            lazyImages.forEach(img => loadImage(img));
        }
    }

    /**
     * Load an image
     */
    function loadImage(img) {
        const src = img.getAttribute('data-src') || img.src;
        const srcset = img.getAttribute('data-srcset');

        // Create a new image to preload
        const tempImg = new Image();

        tempImg.onload = function () {
            img.src = src;
            if (srcset) {
                img.srcset = srcset;
            }
            img.classList.add('lazy-loaded');
            img.classList.remove('lazy-loading');
        };

        tempImg.onerror = function () {
            img.classList.add('lazy-error');
            img.classList.remove('lazy-loading');
            // Set a placeholder image on error if available
            if (img.getAttribute('data-placeholder')) {
                img.src = img.getAttribute('data-placeholder');
            }
        };

        img.classList.add('lazy-loading');
        tempImg.src = src;
    }

    /**
     * Add background image lazy loading
     */
    function initBackgroundLazyLoading() {
        const lazyBackgrounds = document.querySelectorAll('[data-bg]');

        if ('IntersectionObserver' in window) {
            const bgObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const element = entry.target;
                        const bgUrl = element.getAttribute('data-bg');
                        element.style.backgroundImage = `url(${bgUrl})`;
                        element.classList.add('bg-loaded');
                        observer.unobserve(element);
                    }
                });
            }, {
                rootMargin: '50px 0px',
                threshold: 0.01
            });

            lazyBackgrounds.forEach(el => {
                el.classList.add('lazy-bg');
                bgObserver.observe(el);
            });
        } else {
            lazyBackgrounds.forEach(el => {
                const bgUrl = el.getAttribute('data-bg');
                el.style.backgroundImage = `url(${bgUrl})`;
                el.classList.add('bg-loaded');
            });
        }
    }

    /**
     * Optimize image quality based on device pixel ratio
     */
    function getOptimizedImageUrl(url, width, quality = 85) {
        // This is a placeholder function
        // In production, you would integrate with an image optimization service
        // like Cloudinary, Imgix, or Django's sorl-thumbnail

        const dpr = window.devicePixelRatio || 1;
        const optimizedWidth = Math.round(width * dpr);

        // Example: If using a CDN that supports query params
        // return `${url}?w=${optimizedWidth}&q=${quality}`;

        return url;
    }

    /**
     * Preload critical images
     */
    function preloadCriticalImages() {
        const criticalImages = document.querySelectorAll('img[data-critical="true"]');

        criticalImages.forEach(img => {
            const link = document.createElement('link');
            link.rel = 'preload';
            link.as = 'image';
            link.href = img.src;
            document.head.appendChild(link);
        });
    }

    /**
     * Add loading state styles
     */
    function addLazyStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .lazy-image {
                opacity: 0;
                transition: opacity 0.3s ease-in-out;
            }
            
            .lazy-loading {
                opacity: 0.5;
                background: linear-gradient(
                    90deg,
                    rgba(26, 26, 26, 0.08) 25%,
                    rgba(26, 26, 26, 0.12) 50%,
                    rgba(26, 26, 26, 0.08) 75%
                );
                background-size: 200% 100%;
                animation: shimmer 1.5s infinite;
            }
            
            .lazy-loaded {
                opacity: 1;
            }
            
            .lazy-error {
                opacity: 0.5;
                filter: grayscale(100%);
            }
            
            .lazy-bg {
                background-color: rgba(26, 26, 26, 0.05);
                transition: background-color 0.3s ease;
            }
            
            .bg-loaded {
                background-color: transparent;
            }
            
            @keyframes shimmer {
                0% { background-position: -200% 0; }
                100% { background-position: 200% 0; }
            }
            
            /* Improve perceived performance with blur-up technique */
            img[data-src] {
                filter: blur(5px);
                transition: filter 0.3s ease;
            }
            
            img.lazy-loaded[data-src] {
                filter: blur(0);
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Initialize everything on DOM ready
     */
    function init() {
        addLazyStyles();
        initLazyLoading();
        initBackgroundLazyLoading();
        preloadCriticalImages();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Export for external use
    window.LazyLoader = {
        init: init,
        loadImage: loadImage,
        getOptimizedImageUrl: getOptimizedImageUrl
    };

})();
