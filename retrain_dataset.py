import requests
import json

class MLMonitorClient:
    """
    Universal ML Observability SDK
    Use this client to securely log model telemetry back to the centralized platform.
    """
    def __init__(self, api_key, host="http://127.0.0.1:5000", verify_ssl=True):
        self.api_key = api_key
        self.host = host.rstrip("/")
        self.verify_ssl = verify_ssl

    def log_prediction(self, prediction, actual=None, confidence=None, features=None, execution_time_ms=0.0):
        """
        Log a single prediction event.
        :param prediction: Output class from the ML model (str/int)
        :param actual: Ground truth label, if available during inference (str/int)
        :param confidence: Probability score [0.0 - 1.0] (float)
        :param features: Dictionary of input data used for the prediction (dict)
        :param execution_time_ms: How long the model took to inference (float)
        """
        payload = {
            "api_key": self.api_key,
            "prediction": prediction,
            "actual": actual,
            "confidence": confidence,
            "features": features if features else {},
            "latency_ms": execution_time_ms
        }
        
        try:
            url = f"{self.host}/api/v1/telemetry"
            resp = requests.post(url, json=payload, verify=self.verify_ssl)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            print(f"[MLMonitor] Delivery failed: {str(e)}")
            return {"status": "error", "message": str(e)}
