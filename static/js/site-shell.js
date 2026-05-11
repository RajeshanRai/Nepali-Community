(function () {
    document.addEventListener('DOMContentLoaded', function () {
        if (window.AOS) {
            window.AOS.init({
                duration: 800,
                once: true,
                offset: 100,
                easing: 'ease-in-out'
            });
        }
    });
})();
