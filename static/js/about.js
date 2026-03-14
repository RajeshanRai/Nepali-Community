/**
 * About Page - Animations & Interactions
 * Modern SaaS-quality animations with vanilla JavaScript
 */

(function () {
    'use strict';

    // =====================================================
    // SCROLL REVEAL ANIMATIONS
    // =====================================================

    class ScrollReveal {
        constructor() {
            this.observerOptions = {
                threshold: 0.1,
                rootMargin: '0px 0px -50px 0px'
            };
            this.init();
        }

        init() {
            // Target all animatable elements
            const elements = document.querySelectorAll(
                '.hero-text, .hero-visual, .mission-grid, .stats-card, .team-member-card, ' +
                '.timeline-item, .impact-card, .cta-content'
            );

            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.style.opacity = '1';
                        this.observer.unobserve(entry.target);
                    }
                });
            }, this.observerOptions);

            elements.forEach(el => {
                this.observer.observe(el);
            });
        }
    }

    // =====================================================
    // ANIMATED COUNTER
    // =====================================================

    class AnimatedCounter {
        constructor() {
            this.counters = document.querySelectorAll('[data-target]');
            this.init();
        }

        init() {
            const observerOptions = {
                threshold: 0.5,
                rootMargin: '0px'
            };

            this.observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting && !entry.target.dataset.animated) {
                        this.animateCounter(entry.target);
                        entry.target.dataset.animated = 'true';
                    }
                });
            }, observerOptions);

            this.counters.forEach(counter => {
                this.observer.observe(counter);
            });
        }

        animateCounter(element) {
            const target = parseInt(element.dataset.target);
            const duration = 2000; // 2 seconds
            const startTime = Date.now();
            const startValue = 0;

            const updateCounter = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);

                // Easing function (easeOutQuad)
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                const currentValue = Math.floor(startValue + (target - startValue) * easeProgress);

                element.textContent = this.formatNumber(currentValue);

                if (progress < 1) {
                    requestAnimationFrame(updateCounter);
                }
            };

            requestAnimationFrame(updateCounter);
        }

        formatNumber(num) {
            if (num >= 1000) {
                return (num / 1000).toFixed(1).replace(/\.0$/, '') + 'k+';
            }
            return num.toString();
        }
    }

    // =====================================================
    // PARALLAX EFFECT
    // =====================================================

    class ParallaxEffect {
        constructor() {
            this.elements = document.querySelectorAll('[data-parallax]');
            this.speed = 0.5;
            this.init();
        }

        init() {
            if (this.elements.length === 0) return;
            window.addEventListener('scroll', () => this.update(), { passive: true });
        }

        update() {
            const scrolled = window.pageYOffset;

            this.elements.forEach(element => {
                const speed = element.dataset.parallax || this.speed;
                element.style.transform = `translateY(${scrolled * speed}px)`;
            });
        }
    }

    // =====================================================
    // SMOOTH SCROLL TO SECTION
    // =====================================================

    class SmoothScroll {
        constructor() {
            this.links = document.querySelectorAll('a[href^="#"]');
            this.init();
        }

        init() {
            this.links.forEach(link => {
                link.addEventListener('click', (e) => this.handleClick(e));
            });
        }

        handleClick(e) {
            const href = e.currentTarget.getAttribute('href');
            if (href === '#') return;

            const target = document.querySelector(href);
            if (!target) return;

            e.preventDefault();

            const offsetTop = target.offsetTop - 80;
            window.scrollTo({
                top: offsetTop,
                behavior: 'smooth'
            });
        }
    }

    // =====================================================
    // HOVER EFFECTS FOR INTERACTIVE ELEMENTS
    // =====================================================

    class InteractiveElements {
        constructor() {
            this.init();
        }

        init() {
            this.setupMissionCardHover();
            this.setupTeamCardHover();
            this.setupImpactCardHover();
            this.setupButtonEffects();
        }

        setupMissionCardHover() {
            const cards = document.querySelectorAll('.mission-card');
            cards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    card.style.transform = 'translateY(-8px)';
                });
                card.addEventListener('mouseleave', () => {
                    card.style.transform = 'translateY(0)';
                });
            });
        }

        setupTeamCardHover() {
            const cards = document.querySelectorAll('.team-member-card');
            cards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    const image = card.querySelector('.member-image');
                    if (image) {
                        image.style.transform = 'scale(1.1)';
                    }
                });
                card.addEventListener('mouseleave', () => {
                    const image = card.querySelector('.member-image');
                    if (image) {
                        image.style.transform = 'scale(1)';
                    }
                });
            });
        }

        setupImpactCardHover() {
            const cards = document.querySelectorAll('.impact-card');
            cards.forEach(card => {
                card.addEventListener('mouseenter', () => {
                    const icon = card.querySelector('.impact-icon');
                    if (icon) {
                        icon.style.transform = 'rotate(10deg) scale(1.1)';
                    }
                });
                card.addEventListener('mouseleave', () => {
                    const icon = card.querySelector('.impact-icon');
                    if (icon) {
                        icon.style.transform = 'rotate(0deg) scale(1)';
                    }
                });
            });
        }

        setupButtonEffects() {
            const buttons = document.querySelectorAll('.btn');
            buttons.forEach(button => {
                button.addEventListener('click', (e) => this.createRipple(e, button));
            });
        }

        createRipple(e, button) {
            const rect = button.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            const ripple = document.createElement('div');
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.className = 'ripple';
            ripple.style.position = 'absolute';
            ripple.style.background = 'rgba(255, 255, 255, 0.5)';
            ripple.style.borderRadius = '50%';
            ripple.style.pointerEvents = 'none';
            ripple.style.animation = 'rippleEffect 0.6s ease-out';

            button.style.position = 'relative';
            button.style.overflow = 'hidden';
            button.appendChild(ripple);

            setTimeout(() => ripple.remove(), 600);
        }
    }

    // =====================================================
    // STAGGER ANIMATIONS
    // =====================================================

    class StaggerAnimation {
        constructor() {
            this.init();
        }

        init() {
            this.staggerElements('.stats-grid .stat-card');
            this.staggerElements('.team-grid .team-member-card');
            this.staggerElements('.impact-grid .impact-card');
        }

        staggerElements(selector) {
            const elements = document.querySelectorAll(selector);
            elements.forEach((el, index) => {
                const delay = index * 100;
                el.style.setProperty('--animation-delay', delay + 'ms');
            });
        }
    }

    // =====================================================
    // HEADER VISIBILITY ON SCROLL
    // =====================================================

    class SectionVisibility {
        constructor() {
            this.init();
        }

        init() {
            const observer = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('visible');
                    }
                });
            }, { threshold: 0.1 });

            document.querySelectorAll('.section-header').forEach(header => {
                observer.observe(header);
            });
        }
    }

    // =====================================================
    // ADD RIPPLE EFFECT KEYFRAMES
    // =====================================================

    function addRippleEffect() {
        const style = document.createElement('style');
        style.textContent = `
            @keyframes rippleEffect {
                to {
                    transform: scale(4);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // =====================================================
    // INITIALIZATION
    // =====================================================

    document.addEventListener('DOMContentLoaded', () => {
        // Initialize all modules
        new ScrollReveal();
        new AnimatedCounter();
        new ParallaxEffect();
        new SmoothScroll();
        new InteractiveElements();
        new StaggerAnimation();
        new SectionVisibility();
        addRippleEffect();

        // Smooth page entrance
        document.documentElement.style.scrollBehavior = 'smooth';

        // Log initialization
        console.log('About page animations initialized ✨');
    });

    // Handle visibility change for animations
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            document.querySelectorAll('*').forEach(el => {
                if (el.style.animation) {
                    el.style.animationPlayState = 'paused';
                }
            });
        } else {
            document.querySelectorAll('*').forEach(el => {
                if (el.style.animation) {
                    el.style.animationPlayState = 'running';
                }
            });
        }
    });

})();
