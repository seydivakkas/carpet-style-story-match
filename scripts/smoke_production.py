"""
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

Production Operational Smoke Test Utility.
Executes non-mutating HTTP read checks against live production endpoints.
"""
import os
import sys
import urllib.request
import urllib.error


def check_url(name: str, url: str, timeout: int = 5) -> bool:
    print(f"Checking [{name}]: {url} ...", end=" ")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ProductionSmokeTest/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                print(f"PASS ({resp.status} OK)")
                return True
            else:
                print(f"FAIL (HTTP {resp.status})")
                return False
    except urllib.error.HTTPError as exc:
        print(f"FAIL (HTTP {exc.code})")
        return False
    except Exception as exc:
        print(f"FAIL ({exc})")
        return False


def main() -> None:
    api_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
    web_url = os.getenv("WEB_BASE_URL", "http://localhost:3000").rstrip("/")

    print("============================================================")
    print("Production Operational Smoke Test")
    print("============================================================")

    endpoints = [
        ("API Liveness Probe", f"{api_url}/health/live"),
        ("API Readiness Probe", f"{api_url}/health/ready"),
        ("API Meta Endpoint", f"{api_url}/api/v1/meta/style-dna"),
        ("API Catalog Endpoint", f"{api_url}/api/v1/carpets"),
        ("Web Frontend Home", f"{web_url}/")
    ]

    results = []
    for name, url in endpoints:
        results.append(check_url(name, url))

    print("------------------------------------------------------------")
    passed = sum(results)
    total = len(results)
    print(f"Smoke Test Summary: {passed}/{total} endpoints passed.")
    print("============================================================")

    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
