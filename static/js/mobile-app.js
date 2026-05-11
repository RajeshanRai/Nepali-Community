(function () {
    const root = document.documentElement;

    function setViewportUnit() {
        const vh = window.innerHeight * 0.01;
        root.style.setProperty('--app-vh', `${vh}px`);
    }

    function setDeviceFlags() {
        const isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        if (isTouch) {
            root.classList.add('is-touch');
        }

        const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
        if (isStandalone) {
            root.classList.add('is-standalone');
        }
    }

    window.addEventListener('resize', setViewportUnit, { passive: true });
    window.addEventListener('orientationchange', setViewportUnit, { passive: true });

    setViewportUnit();
    setDeviceFlags();
})();