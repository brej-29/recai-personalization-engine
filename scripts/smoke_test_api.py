import os

import httpx


def main() -> None:
    base_url = os.getenv("RECAI_BASE_URL", "http://localhost:8000")

    print(f"[INFO] Pinging {base_url}/health")
    resp = httpx.get(f"{base_url}/health", timeout=5.0)
    print(resp.status_code, resp.json())

    print(f"[INFO] Pinging {base_url}/v1/recommendations?user_id=1&strategy=popular")
    resp = httpx.get(f"{base_url}/v1/recommendations", params={"user_id": 1, "strategy": "popular"}, timeout=5.0)
    print(resp.status_code, resp.json())


if __name__ == "__main__":
    main()