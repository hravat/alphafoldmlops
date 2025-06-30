from prometheus_client import start_http_server

if __name__ == "__main__":
    # Start Prometheus HTTP server on port 8082
    start_http_server(8082)
    print("Prometheus metrics server started at http://localhost:8082/metrics")

    # Keep the script alive
    import time
    while True:
        time.sleep(3600)
