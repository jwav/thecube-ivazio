from flask import Flask, request, jsonify, render_template, make_response
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
from queue import Queue
import threading
from werkzeug.serving import make_server

CUBEWEBAPP_PASSWORD = "pwd"
CUBEWEBAPP_PORT = 5555
CUBEWEBAPP_HOST = "0.0.0.0"
# CUBEWEBAPP_HOST = "localhost"

# TODO: handle extraction of destination and command from the received message
class CubeWebAppReceivedCommand:
    def __init__(self, request_id, full_command):
        self.request_id = request_id
        self.full_command = full_command

class CubeWebAppServer:
    def __init__(self):
        self.WEBAPP_PASSWORD = CUBEWEBAPP_PASSWORD
        self.command_queue = Queue()
        self.response_dict = {}
        self.app = Flask(__name__)
        self._add_routes()
        self.server = None

    def _derive_key(self, password: str) -> bytes:
        """Derive a key directly from the password using SHA-256."""
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(password.encode())
        return digest.finalize()

    def _decrypt(self, encrypted_message: str, key: bytes) -> str:
        data = base64.b64decode(encrypted_message)
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_message = decryptor.update(data) + decryptor.finalize()
        return self._unpad_pkcs7(decrypted_message).decode('utf-8')

    def _unpad_pkcs7(self, padded_message: bytes) -> bytes:
        padding_length = padded_message[-1]
        return padded_message[:-padding_length]

    def _add_routes(self):
        @self.app.route('/')
        def index():
            return render_template('cubewebapp.html')

        @self.app.route('/action', methods=['POST'])
        def action():
            data = request.json
            request_id = threading.get_ident()
            print("received encrypted message: ", data.get('fullcommand'))
            encrypted_message = data.get('fullcommand')
            key = self._derive_key(self.WEBAPP_PASSWORD)

            try:
                decrypted_message = self._decrypt(encrypted_message, key)
                print("decrypted message: ", decrypted_message)
                if not decrypted_message:
                    raise Exception("Mot de passe erronné")
                self.command_queue.put(CubeWebAppReceivedCommand(request_id, decrypted_message))
                response_message = "Commande reçue"

                def generate_reply():
                    while request_id not in self.response_dict:
                        pass
                    reply_msg = self.response_dict.pop(request_id)
                    return jsonify(message=reply_msg)

                return generate_reply()

            except Exception as e:
                response_message = f"Erreur: {e}"
                print("Error decrypting message: ", e)
                return jsonify(message=response_message)

    def run(self):
        self.server = make_server(CUBEWEBAPP_HOST, CUBEWEBAPP_PORT, self.app)  # Bind to all interfaces
        self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.shutdown()

    def get_oldest_command(self):
        if not self.command_queue.empty():
            return self.command_queue.get()
        return None

    def remove_oldest_command(self):
        if not self.command_queue.empty():
            self.command_queue.get()

    def pop_oldest_command(self):
        if not self.command_queue.empty():
            return self.command_queue.get()
        return None

    def has_commands(self):
        return not self.command_queue.empty()

    def send_reply_ok(self, received_command: CubeWebAppReceivedCommand):
        request_id = received_command.request_id
        command = received_command.full_command
        reply_msg = f"Commande '{command}' exécutée"
        self.response_dict[request_id] = reply_msg
        print(f"Reply sent: {reply_msg}")

    def send_reply_error(self, received_command: CubeWebAppReceivedCommand, error_message: str):
        request_id = received_command.request_id
        reply_msg = f"Erreur: {error_message}"
        self.response_dict[request_id] = reply_msg
        print(f"Error reply sent: {reply_msg}")


# Example usage:
if __name__ == '__main__':
    server = CubeWebAppServer()
    server_thread = threading.Thread(target=server.run)
    server_thread.start()

    print("Server started.")  # Indicate that the server has started.

    # In a real application, the following part would be part of a different module or thread.
    try:
        import time
        time.sleep(1)  # Wait for the server to start

        # Example of retrieving and processing commands
        while True:
            received_command = server.get_oldest_command()
            if received_command:
                print(f"Processing command: {received_command.command}")

                server.send_reply_ok(received_command)
            time.sleep(1)  # Polling interval
    except KeyboardInterrupt:
        print("Stopping server...")
        server.stop()
        server_thread.join()
