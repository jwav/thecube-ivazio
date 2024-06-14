from flask import Flask, Response, send_from_directory
import threading
import queue
import os
import time
from thecubeivazio.cube_logger import CubeLogger

class CubeHttpServer:
    DEFAULT_PORT = 8000  # Default port for the server
    EVENT_REFRESH_PLAYING_TEAMS = 'refresh_playing_teams'
    EVENT_REFRESH_HIGHSCORES = 'refresh_highscores'

    def __init__(self, directory, quiet=True):
        self._directory = directory
        self.port = self.DEFAULT_PORT
        self.flask_app = Flask(__name__)
        self.clients = []
        self.log = CubeLogger("CubeHttpServer")
        self.setup_routes()
        self.server_thread = threading.Thread(target=self._start_server_thread)
        self.server_thread.daemon = True

    def setup_routes(self):
        @self.flask_app.route('/stream')
        def stream():
            return self.stream()

        @self.flask_app.route('/')
        def root():
            return send_from_directory(self._directory, 'highscores_main.html')

        @self.flask_app.route('/<path:filename>')
        def static_files(filename):
            return send_from_directory(self._directory, filename)

    def stream(self):
        def event_stream():
            q = queue.Queue()
            self.clients.append(q)
            try:
                while True:
                    result = q.get()
                    yield f'data: {result}\n\n'
            except GeneratorExit:
                self.clients.remove(q)
        return Response(event_stream(), content_type='text/event-stream')

    def run(self):
        self.server_thread.start()

    def _start_server_thread(self):
        self.flask_app.run(port=self.port, debug=False, use_reloader=False)

    def stop(self):
        self.log.info("Shutting down event sender.")
        for client in self.clients:
            client.put('data: server_shutdown\n\n')
        self.clients.clear()
        self.log.info("Event sender shut down.")

    def notify_clients(self, message):
        self.log.info(f"Sending event: {message}")  # Trace line for debugging
        for client in self.clients:
            client.put(message)

    def send_refresh_playing_teams(self):
        self.notify_clients(self.EVENT_REFRESH_PLAYING_TEAMS)

    def send_refresh_highscores(self):
        self.notify_clients(self.EVENT_REFRESH_HIGHSCORES)

def test_CubeHttpServer():
    server = CubeHttpServer("/mnt/shared/thecube-ivazio/thecubeivazio/scores_screen")
    server.run()

    try:
        while True:
            time.sleep(1)
            server.send_refresh_playing_teams()  # Example event trigger
            server.send_refresh_highscores()  # Example event trigger
    except KeyboardInterrupt:
        server.stop()
        print("Shutting down.")

if __name__ == '__main__':
    test_CubeHttpServer()
