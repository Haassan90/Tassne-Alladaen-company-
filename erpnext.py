import os
import requests
from typing import List, Dict

# =====================================================
# ERP CONFIG (SAFE)
# =====================================================
ERP_URL = os.getenv("ERP_URL", "https://your-erp-domain.com")
API_KEY = os.getenv("ERP_API_KEY", "YOUR_API_KEY")
API_SECRET = os.getenv("ERP_API_SECRET", "YOUR_API_SECRET")

TIMEOUT = 10


# =====================================================
# GET WORK ORDERS FROM ERPNEXT
# =====================================================
def get_work_orders() -> List[Dict]:
    """
    Fetch active Work Orders from ERPNext.
    Safe for background loops (Step-12 ready).
    """

    if not ERP_URL or not API_KEY or not API_SECRET:
        print("⚠ ERP credentials not configured")
        return []

    url = f"{ERP_URL}/api/resource/Work Order"

    headers = {
        "Authorization": f"token {API_KEY}:{API_SECRET}",
        "Accept": "application/json"
    }

    params = {
        "fields": (
            '["name","qty","produced_qty","status",'
            '"custom_machine_id","custom_pipe_size","custom_location"]'
        ),
        "filters": (
            '[["status","in",["In Process","Not Started"]]]'
        )
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=TIMEOUT
        )
        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            print("⚠ ERP response invalid format")
            return []

        return payload.get("data", []) or []

    except requests.exceptions.Timeout:
        print("⏱ ERP request timeout")
    except requests.exceptions.RequestException as e:
        print("❌ ERP request failed:", e)
    except Exception as e:
        print("❌ ERP unknown error:", e)

    return []
