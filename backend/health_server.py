"""
Simple HTTP health check server for Cloud Run compatibility.

Cloud Run requires services to respond to HTTP requests on the configured port.
This module provides a lightweight health check endpoint that runs in a background thread.
"""

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler that responds to health check requests."""
    
    def do_GET(self):
        """Handle GET requests for health checks."""
        if self.path in ['/health', '/', '/healthz']:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress HTTP access logs to avoid cluttering application logs."""
        pass


def start_health_server(port=8080):
    """
    Start a simple HTTP health check server in a background thread.
    
    Args:
        port: Port number to listen on (default: 8080)
        
    Returns:
        HTTPServer instance
    """
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HEALTH] HTTP server started on port {port}", flush=True)
    return server
