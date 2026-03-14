// Donation Page JavaScript - donate.js

document.addEventListener('DOMContentLoaded', function () {
    initializeDonationForm();
});

/**
 * Initialize donation form elements and event listeners
 */
function initializeDonationForm() {
    const tierRadios = document.querySelectorAll('input[name="donation_amount"]');
    const customContainer = document.getElementById('customAmountContainer');
    const customInput = document.querySelector('input[name="custom_amount"]');
    const transferAmount = document.getElementById('transferAmount');
    const submitBtn = document.getElementById('submitBtn');
    const donationForm = document.getElementById('donationForm');
    const interactSection = document.getElementById('interactSection');
    const cardSection = document.getElementById('cardSection');

    // Handle tier selection
    if (tierRadios.length > 0) {
        tierRadios.forEach(radio => {
            radio.addEventListener('change', function () {
                handleTierChange(this, customContainer, customInput, transferAmount);
            });
        });
    }

    // Update amount display on custom input
    if (customInput) {
        customInput.addEventListener('input', function () {
            if (this.value && transferAmount) {
                transferAmount.textContent = this.value;
            }
        });
    }

    // Form submission
    if (donationForm) {
        donationForm.addEventListener('submit', function (e) {
            handleFormSubmission(e, submitBtn);
        });
    }

    // Initialize payment method display
    const paymentSelector = document.querySelector('.payment-method-selector');
    const selectedPayment = paymentSelector ? paymentSelector.dataset.selectedPayment : 'interact';
    const paymentRadio = document.querySelector('input[name="payment_method"][value="' + selectedPayment + '"]');
    const fallbackRadio = document.querySelector('input[name="payment_method"]');
    const activeRadio = paymentRadio || fallbackRadio;

    if (activeRadio) {
        activeRadio.checked = true;
        togglePaymentMethod(activeRadio.value);
    }

    // Set initial transfer amount
    const checked = document.querySelector('input[name="donation_amount"]:checked');
    if (checked && transferAmount) {
        transferAmount.textContent = checked.value === 'custom' ? '?' : checked.value;
    }
}

/**
 * Handle tier selection change
 */
function handleTierChange(radio, customContainer, customInput, transferAmount) {
    if (radio.value === 'custom') {
        customContainer.classList.add('show');
        customInput.focus();
        if (transferAmount) transferAmount.textContent = '?';
    } else {
        customContainer.classList.remove('show');
        if (transferAmount) transferAmount.textContent = radio.value;
    }
}

/**
 * Toggle payment method sections
 * @param {string} method - Payment method ('interact' or 'card')
 */
function togglePaymentMethod(method) {
    const interactSection = document.getElementById('interactSection');
    const cardSection = document.getElementById('cardSection');

    if (method === 'interact') {
        if (interactSection) interactSection.style.display = 'block';
        if (cardSection) cardSection.style.display = 'none';
        // Clear card fields
        clearCardFields();
    } else if (method === 'card') {
        if (interactSection) interactSection.style.display = 'none';
        if (cardSection) cardSection.style.display = 'block';
        // Clear interact email
        clearInteractFields();
    }
}

/**
 * Clear all card form fields
 */
function clearCardFields() {
    const fields = ['card_name', 'card_number', 'card_expiry', 'card_cvv'];
    fields.forEach(fieldName => {
        const field = document.querySelector(`input[name="${fieldName}"]`);
        if (field) field.value = '';
    });
}

/**
 * Clear interact form fields
 */
function clearInteractFields() {
    const interactEmail = document.querySelector('input[name="interact_email"]');
    if (interactEmail) interactEmail.value = '';
}

/**
 * Handle form submission with validation
 */
function handleFormSubmission(e, submitBtn) {
    const selected = document.querySelector('input[name="donation_amount"]:checked');
    const donorName = document.querySelector('input[name="donor_name"]');
    const anonymous = document.querySelector('input[name="anonymous"]');
    const selectedPayment = document.querySelector('input[name="payment_method"]:checked');

    const donorNameValue = donorName ? donorName.value.trim() : '';
    const anonymousChecked = anonymous ? anonymous.checked : false;
    const paymentMethod = selectedPayment ? selectedPayment.value : '';

    // Validate donation amount selected
    if (!selected) {
        e.preventDefault();
        alert('Please select a donation amount.');
        return false;
    }

    // Validate donor name or anonymous
    if (!anonymousChecked && !donorNameValue) {
        e.preventDefault();
        alert('Please enter your name or check the anonymous option.');
        return false;
    }

    // Validate payment method selected
    if (!paymentMethod) {
        e.preventDefault();
        alert('Please select a payment method.');
        return false;
    }

    // Validate payment method specific fields
    if (paymentMethod === 'interact') {
        if (!validateInteractPayment()) {
            e.preventDefault();
            return false;
        }
    } else if (paymentMethod === 'card') {
        if (!validateCardPayment()) {
            e.preventDefault();
            return false;
        }
    }

    // Disable submit button and show processing state
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    }

    // Submit the form normally - it will redirect to success page
}

/**
 * Validate Interact payment fields
 */
function validateInteractPayment() {
    const interactEmail = document.querySelector('input[name="interact_email"]');
    const emailValue = interactEmail ? interactEmail.value.trim() : '';

    if (!emailValue) {
        alert('Please provide your Interact email address.');
        return false;
    }
    return true;
}

/**
 * Validate card payment fields
 */
function validateCardPayment() {
    const cardName = document.querySelector('input[name="card_name"]');
    const cardNumber = document.querySelector('input[name="card_number"]');
    const cardExpiry = document.querySelector('input[name="card_expiry"]');
    const cardCvv = document.querySelector('input[name="card_cvv"]');

    const cardNameValue = cardName ? cardName.value.trim() : '';
    const cardNumberValue = cardNumber ? cardNumber.value.trim() : '';
    const cardExpiryValue = cardExpiry ? cardExpiry.value.trim() : '';
    const cardCvvValue = cardCvv ? cardCvv.value.trim() : '';

    if (!cardNameValue) {
        alert('Please enter the name on your card.');
        return false;
    }
    if (!cardNumberValue) {
        alert('Please enter your card number.');
        return false;
    }
    if (!cardExpiryValue) {
        alert('Please enter the card expiry date (MM/YY).');
        return false;
    }
    if (!cardCvvValue) {
        alert('Please enter your card security code (CVV).');
        return false;
    }

    return true;
}
