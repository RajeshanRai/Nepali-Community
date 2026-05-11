
                body: form
            })
                .then(async r => {
                    const data = await r.json().catch(() => ({ success: false, message: 'Invalid server response' }));
                    return { ok: r.ok, data };
                })
                .then(data => {
                    const res = document.getElementById('request-result');
                    res.style.display = 'block';
                    res.textContent = data.data?.message || 'Submitted';
                    if (data.ok && data.data?.success) {
                        res.style.color = 'green';
                        eventRequestForm.reset();
                    } else {
                        res.style.color = 'red';
                    }
                })
                .catch(err => {
                    console.error(err);
                    const res = document.getElementById('request-result');
                    res.style.display = 'block';
                    res.style.color = 'red';
                    res.textContent = 'An error occurred while submitting the request.';
                });
        });
    }
});
