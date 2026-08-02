"""Semantic deployment verifier; HTTP success alone is never sufficient."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from build_info import build_information, load_deployment_manifest


REQUIRED_MARKERS = (
    "Workflow status / 流程状态",
    "Continue to explanation / 进入想法解释",
)
FORBIDDEN_MARKERS = ("Select an idea in Part 2.",)


def expected_deployment() -> dict[str, object]:
    manifest = load_deployment_manifest(ROOT) or {}
    info = build_information("lightweight")
    return {
        "expected_commit": info["commit_sha"],
        "expected_app_fingerprint": manifest.get("app_source_fingerprint"),
        "expected_pipeline_version": manifest.get("pipeline_version"),
        "required_markers": list(REQUIRED_MARKERS),
        "forbidden_markers": list(FORBIDDEN_MARKERS),
    }


def verify_html(html: str) -> dict[str, object]:
    expected = expected_deployment()
    missing = [marker for marker in REQUIRED_MARKERS if marker not in html]
    forbidden = [marker for marker in FORBIDDEN_MARKERS if marker in html]
    expected["status"] = "MATCH" if not missing and not forbidden else "SEMANTIC_MISMATCH"
    expected["missing_markers"] = missing
    expected["forbidden_markers_found"] = forbidden
    return expected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?")
    args = parser.parse_args()
    if not args.url:
        print(json.dumps(expected_deployment(), indent=2, ensure_ascii=False))
        return 0
    try:
        request = Request(args.url, headers={"User-Agent": "deployment-semantic-check/1"})
        with urlopen(request, timeout=20) as response:
            html = response.read(1_000_000).decode("utf-8", "replace")
            final_url = response.geturl()
    except (HTTPError, URLError, TimeoutError) as exc:
        print(json.dumps({
            **expected_deployment(),
            "status": "INACCESSIBLE",
            "limitation": f"{type(exc).__name__}: {' '.join(str(exc).split())[:300]}",
        }, indent=2, ensure_ascii=False))
        return 2
    result = verify_html(html)
    result["final_url"] = final_url
    if result["status"] != "MATCH":
        result["limitation"] = (
            "Streamlit renders application semantics dynamically; use browser "
            "automation when markers are absent from the initial HTML."
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
