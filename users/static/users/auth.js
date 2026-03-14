(function () {
    'use strict';

    function getControl(input) {
        return input ? input.closest('[data-field]') : null;
    }

    function setFilledState(input) {
        var control = getControl(input);
        if (!control) {
            return;
        }

        control.classList.toggle('is-filled', Boolean((input.value || '').trim()));
    }

    function setValidationState(input, state) {
        var control = getControl(input);
        if (!control) {
            return;
        }

        control.classList.remove('is-valid', 'is-invalid');
        input.removeAttribute('aria-invalid');

        if (state === 'valid') {
            control.classList.add('is-valid');
            return;
        }

        if (state === 'invalid') {
            control.classList.add('is-invalid');
            input.setAttribute('aria-invalid', 'true');
        }
    }

    function shakeField(input) {
        var control = getControl(input);
        if (!control) {
            return;
        }

        control.classList.remove('is-shaking');
        void control.offsetWidth;
        control.classList.add('is-shaking');

        window.setTimeout(function () {
            control.classList.remove('is-shaking');
        }, 360);
    }

    function passwordScore(value) {
        var score = 0;
        if (value.length >= 8) score += 1;
        if (/[A-Z]/.test(value)) score += 1;
        if (/[a-z]/.test(value)) score += 1;
        if (/\d/.test(value)) score += 1;
        if (/[^A-Za-z0-9]/.test(value)) score += 1;
        return score;
    }

    function initStrength() {
        var input = document.getElementById('id_password');
        var fill = document.getElementById('strengthFill');
        var label = document.getElementById('strengthLabel');
        if (!input || !fill || !label) {
            return;
        }

        function update() {
            var value = input.value || '';
            var score = passwordScore(value);
            fill.className = 'auth-strength-fill';

            if (!value.length) {
                fill.style.width = '0%';
                label.textContent = 'Use 8+ characters with uppercase, lowercase, number, and symbol.';
                return;
            }

            if (score <= 2) {
                fill.style.width = '28%';
                label.textContent = 'Weak password. Add more variety.';
                return;
            }

            if (score === 3) {
                fill.classList.add('s-fair');
                fill.style.width = '52%';
                label.textContent = 'Fair password. Add one more layer of complexity.';
                return;
            }

            if (score === 4) {
                fill.classList.add('s-good');
                fill.style.width = '78%';
                label.textContent = 'Good password.';
                return;
            }

            fill.classList.add('s-strong');
            fill.style.width = '100%';
            label.textContent = 'Strong password.';
        }

        input.addEventListener('input', update);
        update();
    }

    function initPasswordMatch() {
        var password = document.getElementById('id_password');
        var confirm = document.getElementById('id_password_confirm');
        var status = document.getElementById('matchStatus');
        if (!password || !confirm || !status) {
            return;
        }

        function update() {
            status.className = 'auth-match';

            if (!confirm.value.length) {
                status.textContent = '';
                return;
            }

            if (password.value === confirm.value) {
                status.classList.add('ok');
                status.textContent = 'Passwords match.';
                return;
            }

            status.classList.add('err');
            status.textContent = 'Passwords do not match.';
        }

        password.addEventListener('input', update);
        confirm.addEventListener('input', update);
        update();
    }

    function validateField(input, onSubmit) {
        var value = (input.value || '').trim();
        var required = input.hasAttribute('required');
        var valid = true;

        if (!required && !value) {
            setValidationState(input, null);
            return true;
        }

        if (required && !value) {
            valid = false;
        } else if (value) {
            valid = input.checkValidity();
        }

        if (input.id === 'id_password_confirm') {
            var password = document.getElementById('id_password');
            if (password && input.value && password.value !== input.value) {
                valid = false;
            }
        }

        if (valid) {
            setValidationState(input, value ? 'valid' : null);
        } else {
            setValidationState(input, 'invalid');
            if (onSubmit) {
                shakeField(input);
            }
        }

        return valid;
    }

    function initFieldBehavior() {
        document.querySelectorAll('.auth-control').forEach(function (control, index) {
            window.setTimeout(function () {
                control.classList.add('is-ready');
            }, 60 + (index * 45));
        });

        document.querySelectorAll('.auth-input').forEach(function (input) {
            setFilledState(input);

            input.addEventListener('focus', function () {
                var control = getControl(input);
                if (control) {
                    control.classList.add('is-focused');
                }
            });

            input.addEventListener('blur', function () {
                var control = getControl(input);
                if (control) {
                    control.classList.remove('is-focused');
                }

                setFilledState(input);
                validateField(input, false);
            });

            input.addEventListener('input', function () {
                setFilledState(input);
                validateField(input, false);
            });
        });
    }

    function initRippleEffect() {
        document.querySelectorAll('.auth-submit, .auth-social-btn').forEach(function (button) {
            button.addEventListener('click', function (event) {
                if (button.disabled) {
                    return;
                }

                var rect = button.getBoundingClientRect();
                var ripple = document.createElement('span');
                var size = Math.max(rect.width, rect.height);

                ripple.className = 'auth-ripple';
                ripple.style.width = size + 'px';
                ripple.style.height = size + 'px';
                ripple.style.left = (event.clientX - rect.left) + 'px';
                ripple.style.top = (event.clientY - rect.top) + 'px';

                button.appendChild(ripple);

                window.setTimeout(function () {
                    ripple.remove();
                }, 620);
            });
        });
    }

    function initFormSubmission() {
        document.querySelectorAll('[data-auth-form]').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                if (form.dataset.submitting === 'true') {
                    event.preventDefault();
                    return;
                }

                var fields = Array.prototype.slice.call(form.querySelectorAll('.auth-input'));
                var firstInvalid = null;

                fields.forEach(function (input) {
                    var isValid = validateField(input, true);
                    if (!isValid && !firstInvalid) {
                        firstInvalid = input;
                    }
                });

                if (firstInvalid) {
                    event.preventDefault();
                    firstInvalid.focus();
                    return;
                }

                form.dataset.submitting = 'true';
                var submitButton = form.querySelector('[data-submit-btn]');
                if (submitButton) {
                    submitButton.classList.add('is-loading');
                    submitButton.disabled = true;
                }
            });
        });
    }

    function initPlaceholderLinks() {
        document.querySelectorAll('[data-placeholder-link]').forEach(function (link) {
            link.addEventListener('click', function (event) {
                event.preventDefault();
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        initFieldBehavior();
        initStrength();
        initPasswordMatch();
        initRippleEffect();
        initFormSubmission();
        initPlaceholderLinks();
    });
})();