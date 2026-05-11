document.addEventListener('DOMContentLoaded', function () {
    var card = document.querySelector('.auth-reset-card');
    if (card) {
        window.requestAnimationFrame(function () {
            card.classList.add('is-visible');
        });
    }

    ['id_new_password1', 'id_new_password2'].forEach(function (id) {
        var input = document.getElementById(id);
        if (!input) return;

        var wrapper = document.createElement('div');
        wrapper.className = 'input-with-toggle';
        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(input);

        var toggle = document.createElement('button');
        toggle.type = 'button';
        toggle.className = 'pw-toggle';
        toggle.textContent = 'Show';
        toggle.setAttribute('aria-label', 'Show password');

        toggle.addEventListener('click', function () {
            var isPassword = input.type === 'password';
            input.type = isPassword ? 'text' : 'password';
            toggle.textContent = isPassword ? 'Hide' : 'Show';
            toggle.setAttribute('aria-label', isPassword ? 'Hide password' : 'Show password');
        });

        wrapper.appendChild(toggle);
    });
});
