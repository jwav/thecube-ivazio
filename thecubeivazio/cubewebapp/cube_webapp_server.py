from flask import Flask, request, jsonify, render_template, make_response
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import base64
from queue import Queue
import threading
from werkzeug.serving import make_server

CUBEWEBAPP_PASSWORD = "pwd"

class CubeWebAppServer:
    def __init__(self):
        self.WEBAPP_PASSWORD = CUBEWEBAPP_PASSWORD
        self.command_queue = Queue()
        self.response_dict = {}
        self.app = Flask(__name__)
        self.add_routes()
        self.server = None

    def derive_key(self, password: str) -> bytes:
        """Derive a key directly from the password using SHA-256."""
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(password.encode())
        return digest.finalize()

    def decrypt(self, encrypted_message: str, key: bytes) -> str:
        data = base64.b64decode(encrypted_message)
        cipher = Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())
        decryptor = cipher.decryptor()
        decrypted_message = decryptor.update(data) + decryptor.finalize()
        return self.unpad_pkcs7(decrypted_message).decode('utf-8')

    def unpad_pkcs7(self, padded_message: bytes) -> bytes:
        padding_length = padded_message[-1]
        return padded_message[:-padding_length]

    def add_routes(self):
        @self.app.route('/')
        def index():
            return render_template('cubewebapp.html')

        @self.app.route('/action', methods=['POST'])
        def action():
            data = request.json
            request_id = threading.get_ident()
            print("received encrypted message: ", data.get('fullcommand'))
            encrypted_message = data.get('fullcommand')
            key = self.derive_key(self.WEBAPP_PASSWORD)

            try:
                decrypted_message = self.decrypt(encrypted_message, key)
                print("decrypted message: ", decrypted_message)
                if not decrypted_message:
                    raise Exception("Mot de passe erronné")
                self.command_queue.put((request_id, decrypted_message))
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
        # self.server = make_server('localhost', 5000, self.app)
        self.server = make_server('0.0.0.0', 5000, self.app)  # Bind to all interfaces
        self.server.serve_forever()

    def stop(self):
        if self.server:
            self.server.shutdown()

    def get_oldest_command(self):
        if not self.command_queue.empty():
            return self.command_queue.get()
        return None

    def send_reply(self, reply_msg: str):
        request_id, reply = reply_msg
        self.response_dict[request_id] = reply
        print(f"Reply sent: {reply}")

# Example usage:
if __name__ == '__main__':
    server = CubeWebAppServer()
    server_thread = threading.Thread(target=server.run)
    server_thread.start()

    # In a real application, the following part would be part of a different module or thread.
    try:
        import time
        time.sleep(1)  # Wait for the server to start

        # Example of retrieving and processing commands
        while True:
            command_tuple = server.get_oldest_command()
            if command_tuple:
                request_id, command = command_tuple
                print(f"Processing command: {command}")
                server.send_reply((request_id, f"Commande '{command}' exécutée"))
            time.sleep(1)  # Polling interval
    except KeyboardInterrupt:
        print("Stopping server...")
        server.stop()
        server_thread.join()
