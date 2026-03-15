(function () {
    const state = {
        confirmResolver: null,
        promptResolver: null,
        pendingFetches: 0,
        loaderTimer: null,
        loaderVisible: false,
        initialized: false
    };

    function qs(id) {
        return document.getElementById(id);
    }

    function mountUi() {
        if (state.initialized) return;
        state.initialized = true;

        const wrapper = document.createElement('div');
        wrapper.innerHTML = `
            <div id="ncvGlobalConfirm" class="ncv-ui-confirm ncv-ui-hidden" role="dialog" aria-modal="true" aria-labelledby="ncvGlobalConfirmTitle">
                <div class="ncv-ui-confirm__card">
                    <div class="ncv-ui-confirm__head">
                        <i class="fas fa-circle-exclamation" aria-hidden="true"></i>
                        <h3 id="ncvGlobalConfirmTitle" class="ncv-ui-confirm__title">Please confirm</h3>
                    </div>
                    <div id="ncvGlobalConfirmBody" class="ncv-ui-confirm__body"></div>
                    <div id="ncvGlobalPromptWrap" class="ncv-ui-confirm__input-wrap ncv-ui-hidden">
                        <input id="ncvGlobalPromptInput" class="ncv-ui-confirm__input" type="text" autocomplete="off">
                    </div>
                    <div class="ncv-ui-confirm__actions">
                        <button id="ncvGlobalConfirmCancel" type="button" class="ncv-ui-btn ncv-ui-btn--ghost">Cancel</button>
                        <button id="ncvGlobalConfirmOk" type="button" class="ncv-ui-btn ncv-ui-btn--primary">Confirm</button>
                    </div>
                </div>
            </div>
            <div id="ncvGlobalLoading" class="ncv-ui-loading ncv-ui-hidden" role="status" aria-live="polite" aria-label="Loading">
                <div class="ncv-ui-loading__box">
                    <div class="ncv-ui-spinner" aria-hidden="true"></div>
                    <div id="ncvGlobalLoadingText" class="ncv-ui-loading__text">Loading...</div>
                </div>
            </div>
        `;

        document.body.appendChild(wrapper);

        qs('ncvGlobalConfirmCancel')?.addEventListener('click', () => resolveConfirm(false));
        qs('ncvGlobalConfirmOk')?.addEventListener('click', () => resolveConfirm(true));
        qs('ncvGlobalConfirm')?.addEventListener('click', (event) => {
            if (event.target === qs('ncvGlobalConfirm')) {
                resolveConfirm(false);
            }
        });

        document.addEventListener('keydown', (event) => {
            const confirmEl = qs('ncvGlobalConfirm');
            if (!confirmEl || confirmEl.classList.contains('ncv-ui-hidden')) return;

            if (event.key === 'Escape') {
                event.preventDefault();
                resolveConfirm(false);
            }

            if (event.key === 'Enter') {
                const promptInput = qs('ncvGlobalPromptInput');
                if (promptInput && document.activeElement === promptInput) {
                    event.preventDefault();
                    resolveConfirm(true);
                }
            }
        });

        bindNavigationLoader();
        patchFetchLoader();
    }

    function openConfirmDialog(options) {
        mountUi();

        const confirmEl = qs('ncvGlobalConfirm');
        const titleEl = qs('ncvGlobalConfirmTitle');
        const bodyEl = qs('ncvGlobalConfirmBody');
        const okEl = qs('ncvGlobalConfirmOk');
        const promptWrap = qs('ncvGlobalPromptWrap');
        const promptInput = qs('ncvGlobalPromptInput');

        titleEl.textContent = options.title || 'Please confirm';
        bodyEl.textContent = options.message || 'Are you sure you want to continue?';
        okEl.textContent = options.okText || 'Confirm';
        okEl.classList.remove('ncv-ui-btn--primary', 'ncv-ui-btn--danger');
        okEl.classList.add(options.variant === 'danger' ? 'ncv-ui-btn--danger' : 'ncv-ui-btn--primary');

        if (options.prompt) {
            promptWrap.classList.remove('ncv-ui-hidden');
            promptInput.value = options.defaultValue || '';
            promptInput.placeholder = options.placeholder || '';
            setTimeout(() => promptInput.focus(), 0);
        } else {
            promptWrap.classList.add('ncv-ui-hidden');
            promptInput.value = '';
            setTimeout(() => okEl.focus(), 0);
        }

        confirmEl.classList.remove('ncv-ui-hidden');
        document.body.classList.add('ncv-ui-lock');

        return new Promise((resolve) => {
            state.confirmResolver = (accepted) => {
                const promptValue = options.prompt ? promptInput.value : '';
                resolve(options.prompt ? (accepted ? promptValue : null) : accepted);
            };
        });
    }

    function resolveConfirm(result) {
        const confirmEl = qs('ncvGlobalConfirm');
        if (confirmEl) {
            confirmEl.classList.add('ncv-ui-hidden');
        }
        document.body.classList.remove('ncv-ui-lock');

        if (typeof state.confirmResolver === 'function') {
            const resolver = state.confirmResolver;
            state.confirmResolver = null;
            resolver(result);
        }
    }

    function showLoader(message) {
        mountUi();
        const loader = qs('ncvGlobalLoading');
        const text = qs('ncvGlobalLoadingText');
        const loadingBox = loader ? loader.querySelector('.ncv-ui-loading__box') : null;
        const spinner = loader ? loader.querySelector('.ncv-ui-spinner') : null;
        if (!loader) return;

        if (message && text) {
            text.textContent = message;
        }

        if (spinner) {
            const orbitDuration = Math.round(760 + Math.random() * 520);
            const pulseDuration = Math.round(1200 + Math.random() * 760);
            const loaderPalettes = [
                {
                    accent: '#ff7a00',
                    accentLight: '#ff9f3f',
                    border: 'rgba(255, 154, 73, 0.55)',
                    shadow: 'rgba(35, 22, 10, 0.30)'
                },
                {
                    accent: '#ff6b35',
                    accentLight: '#ff8f63',
                    border: 'rgba(255, 133, 92, 0.52)',
                    shadow: 'rgba(36, 20, 16, 0.30)'
                },
                {
                    accent: '#e85d04',
                    accentLight: '#f48c42',
                    border: 'rgba(240, 132, 69, 0.52)',
                    shadow: 'rgba(36, 20, 10, 0.30)'
                },
                {
                    accent: '#f97316',
                    accentLight: '#fb923c',
                    border: 'rgba(251, 146, 60, 0.54)',
                    shadow: 'rgba(41, 24, 12, 0.30)'
                }
            ];
            const palette = loaderPalettes[Math.floor(Math.random() * loaderPalettes.length)];

            spinner.style.setProperty('--ncv-ui-orbit-duration', `${orbitDuration}ms`);
            spinner.style.setProperty('--ncv-ui-pulse-duration', `${pulseDuration}ms`);
            spinner.style.setProperty('--ncv-ui-loader-accent', palette.accent);
            spinner.style.setProperty('--ncv-ui-loader-accent-light', palette.accentLight);

            if (loadingBox) {
                loadingBox.style.setProperty('--ncv-ui-loader-accent', palette.accent);
                loadingBox.style.setProperty('--ncv-ui-loader-accent-light', palette.accentLight);
                loadingBox.style.setProperty('--ncv-ui-loader-border', palette.border);
                loadingBox.style.setProperty('--ncv-ui-loader-shadow', palette.shadow);
            }
        }

        loader.classList.remove('ncv-ui-hidden');
        state.loaderVisible = true;
    }

    function hideLoader() {
        const loader = qs('ncvGlobalLoading');
        if (!loader) return;
        loader.classList.add('ncv-ui-hidden');
        state.loaderVisible = false;
    }

    function queueFetchLoaderOn() {
        if (state.loaderTimer) return;
        state.loaderTimer = window.setTimeout(() => {
            state.loaderTimer = null;
            if (state.pendingFetches > 0) {
                showLoader('Loading...');
            }
        }, 180);
    }

    function queueFetchLoaderOff() {
        if (state.pendingFetches > 0) return;
        if (state.loaderTimer) {
            window.clearTimeout(state.loaderTimer);
            state.loaderTimer = null;
        }
        hideLoader();
    }

    function patchFetchLoader() {
        if (!window.fetch || window.fetch.__ncvLoaderPatched) return;

        const originalFetch = window.fetch.bind(window);
        const patchedFetch = function (resource, options) {
            const opts = options || {};
            const headers = opts.headers || {};
            const skipLoader = headers['X-Skip-Loader'] === 'true' || headers['x-skip-loader'] === 'true';

            if (!skipLoader) {
                state.pendingFetches += 1;
                queueFetchLoaderOn();
            }

            return originalFetch(resource, options)
                .finally(() => {
                    if (!skipLoader) {
                        state.pendingFetches = Math.max(0, state.pendingFetches - 1);
                        queueFetchLoaderOff();
                    }
                });
        };

        patchedFetch.__ncvLoaderPatched = true;
        window.fetch = patchedFetch;
    }

    function isSameOrigin(link) {
        try {
            const url = new URL(link.href, window.location.origin);
            return url.origin === window.location.origin;
        } catch {
            return false;
        }
    }

    function bindNavigationLoader() {
        document.addEventListener('click', (event) => {
            const link = event.target.closest('a[href]');
            if (!link) return;
            if (link.dataset.noLoader === 'true') return;
            if (link.target === '_blank') return;
            if (link.hasAttribute('download')) return;
            if (!isSameOrigin(link)) return;

            const href = link.getAttribute('href') || '';
            if (!href || href.startsWith('#') || href.startsWith('javascript:')) return;

            showLoader('Opening page...');
        }, true);

        document.addEventListener('submit', (event) => {
            const form = event.target;
            if (!(form instanceof HTMLFormElement)) return;
            if (form.dataset.noLoader === 'true') return;
            if (form.target === '_blank') return;

            showLoader('Processing...');
        }, true);

        window.addEventListener('pageshow', () => {
            hideLoader();
        });

        window.addEventListener('load', () => {
            hideLoader();
        });
    }

    window.GlobalUI = {
        confirm(input) {
            const options = typeof input === 'string'
                ? { message: input }
                : (input || {});
            return openConfirmDialog(options).then((value) => Boolean(value));
        },
        prompt(input) {
            const options = typeof input === 'string'
                ? { message: input }
                : (input || {});
            return openConfirmDialog({
                title: options.title || 'Enter value',
                message: options.message || '',
                okText: options.okText || 'Submit',
                defaultValue: options.defaultValue || '',
                placeholder: options.placeholder || '',
                prompt: true,
                variant: options.variant || 'primary'
            });
        },
        showLoading(message = 'Loading...') {
            showLoader(message);
        },
        hideLoading() {
            hideLoader();
        }
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', mountUi);
    } else {
        mountUi();
    }
})();
