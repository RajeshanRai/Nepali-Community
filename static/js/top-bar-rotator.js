(function () {
    function initTopBarRotator() {
        var rotator = document.querySelector('[data-topbar-rotator]');
        if (!rotator) {
            return;
        }

        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            return;
        }

        var items = Array.prototype.slice.call(rotator.querySelectorAll('.top-navbar-rotator-item'));
        if (items.length < 2) {
            return;
        }

        var currentIndex = items.findIndex(function (item) {
            return item.classList.contains('is-active');
        });
        var intervalId = null;

        if (currentIndex < 0) {
            currentIndex = 0;
            items[0].classList.add('is-active');
        }

        function setActive(nextIndex) {
            items[currentIndex].classList.remove('is-active');
            currentIndex = nextIndex;
            items[currentIndex].classList.add('is-active');
        }

        function stopRotation() {
            if (intervalId) {
                window.clearInterval(intervalId);
                intervalId = null;
            }
        }

        function startRotation() {
            stopRotation();
            intervalId = window.setInterval(function () {
                setActive((currentIndex + 1) % items.length);
            }, 3600);
        }

        rotator.addEventListener('mouseenter', stopRotation);
        rotator.addEventListener('mouseleave', startRotation);
        rotator.addEventListener('focusin', stopRotation);
        rotator.addEventListener('focusout', startRotation);

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) {
                stopRotation();
                return;
            }

            startRotation();
        });

        startRotation();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTopBarRotator);
    } else {
        initTopBarRotator();
    }
})();