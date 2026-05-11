// Donation Success Page JavaScript

function openBankApp() {
    // Try to use the Payment Request API if available
    if (window.PaymentRequest && typeof PaymentRequest !== 'undefined') {
        // Fallback: Open a new tab with bank instructions
        const email = 'donations@nepalicommunityvancouver.ca';
        const amount = document.getElementById('amountDisplay').textContent.trim().replace('$', '');

        // Create a helper message
        alert('Please open your bank app and send an Interact e-Transfer:\n\n' +
            'Amount: $' + amount + '\n' +
            'To: ' + email + '\n\n' +
            'Your bank app will open now.');
    }

    // Open bank app deeplink or fallback to browser
    const userAgent = navigator.userAgent || navigator.vendor || window.opera;

    // Check for mobile
    const isMobile = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase());

    if (isMobile) {
        // Try common bank app schemes
        const bankApps = [
            'td://open',  // TD
            'scotiabank://home',  // Scotiabank
            'bmo://home',  // BMO
            'rbc://home',  // RBC
            'cibc://home'  // CIBC
        ];

        // Try the first bank app
        for (let app of bankApps) {
            // Try opening the app (won't work from browser, just for reference)
        }
    }

    // Fallback: Show instructions
    showBankInstructions();
}

function showBankInstructions() {
    const email = 'donations@nepalicommunityvancouver.ca';
    const amountElement = document.getElementById('amountDisplay');
    const amount = amountElement ? amountElement.textContent.trim().replace('$', '') : '0';

    // Create a modal or notification
    const instruction = `
        <strong>Manual Steps:</strong><br>
        1. Open your bank's app<br>
        2. Select Interact e-Transfer<br>
        3. Enter amount: $${amount}<br>
        4. Send to: ${email}<br>
        5. Add reference from your confirmation email
    `;

    console.log(instruction);
}

function copyEmail(email, button) {
    // Copy email to clipboard
    navigator.clipboard.writeText(email).then(() => {
        // Visual feedback
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = email;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);

        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');

        setTimeout(() => {
            button.innerHTML = '<i class="fas fa-copy"></i> Copy Email';
            button.classList.remove('copied');
        }, 2000);
    });
}
