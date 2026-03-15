"""Verify SHODAN_API_KEY is set and accepted by Shodan API."""
import sys
import httpx

from app.settings import settings


def main():
    key = (settings.SHODAN_API_KEY or "").strip()
    if not key:
        print("FAIL: SHODAN_API_KEY is not set in .env")
        return 1
    masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
    print(f"Checking SHODAN_API_KEY ({masked})...")

    try:
        r = httpx.get(
            "https://api.shodan.io/account/profile",
            params={"key": key},
            timeout=10.0,
        )
        if r.status_code == 200:
            data = r.json()
            print("OK: Shodan API key is valid.")
            print(f"  Member: {data.get('member', '?')}  Credits: {data.get('credits', '?')}")
            return 0
        print(f"FAIL: Shodan returned HTTP {r.status_code}")
        try:
            err = r.json()
            print(f"  {err.get('error', r.text[:200])}")
        except Exception:
            print(f"  {r.text[:200]}")
        return 1
    except Exception as e:
        print(f"FAIL: {type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
