document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('send').addEventListener('click', function() {
        const password = document.getElementById('password').value;
        const destination = document.getElementById('destination').value;
        const action = document.getElementById('action').value;
        const fullcommand = `${destination} ${action}`;
        const disablePopup = document.getElementById('disablePopup').checked;

        const sendCommand = () => {
            const key = CryptoJS.SHA256(password);
            const encrypted = CryptoJS.AES.encrypt(fullcommand, key, {
                mode: CryptoJS.mode.ECB,
                padding: CryptoJS.pad.Pkcs7
            });
            const encryptedMessage = CryptoJS.enc.Base64.stringify(encrypted.ciphertext);

            fetch('/action', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ fullcommand: encryptedMessage })
            })
            .then(response => response.json())
            .then(data => {
                const messageList = document.getElementById('messageList');
                const listItem = document.createElement('li');
                listItem.textContent = data.message;
                messageList.appendChild(listItem);
            });
        };

        if (disablePopup) {
            sendCommand();
        } else {
            if (confirm(`Envoyer commande '${fullcommand}' ?`)) {
                sendCommand();
            }
        }
    });
});
