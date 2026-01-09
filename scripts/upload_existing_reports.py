#!/usr/bin/env python3
"""Script to upload existing reports to R2 storage."""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from tradingagents.config import R2StorageConfig
from tradingagents.storage.backends.r2 import R2StorageBackend


def main():
    # Load environment variables
    load_dotenv()

    # Create R2 config from environment
    r2_config = R2StorageConfig(
        account_id=os.getenv("R2_ACCOUNT_ID"),
        access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        bucket_name=os.getenv("R2_BUCKET_NAME"),
        endpoint_url=os.getenv("R2_ENDPOINT_URL"),
    )

    if not r2_config.is_configured:
        print("Error: R2 is not configured. Please set R2 environment variables.")
        sys.exit(1)

    print(f"R2 Config: bucket={r2_config.bucket_name}")
    print(f"Endpoint: {r2_config.endpoint_url}")

    # Create R2 backend directly
    reports_dir = Path(__file__).parent.parent / "reports"
    r2_backend = R2StorageBackend(r2_config)

    # Find all report files
    if not reports_dir.exists():
        print(f"\nError: Reports directory not found: {reports_dir}")
        sys.exit(1)

    print(f"\nScanning reports directory: {reports_dir}")

    uploaded_count = 0
    failed_count = 0

    for report_folder in sorted(reports_dir.iterdir()):
        if not report_folder.is_dir():
            continue

        print(f"\n--- {report_folder.name} ---")

        for report_file in sorted(report_folder.iterdir()):
            if not report_file.is_file():
                continue

            # Only upload .pdf and .md files
            if report_file.suffix not in [".pdf", ".md"]:
                continue

            remote_key = f"{report_folder.name}/{report_file.name}"
            print(f"  Uploading: {report_file.name}")

            try:
                result = r2_backend.upload_file(report_file, remote_key)
                print(f"    R2: {result}")
                uploaded_count += 1

                # Get presigned URL
                url = r2_backend.get_url(remote_key)
                if url:
                    print(f"    URL: {url[:80]}...")

            except Exception as e:
                print(f"    Error: {e}")
                failed_count += 1

    print(f"\n=== Summary ===")
    print(f"Uploaded: {uploaded_count} files")
    print(f"Failed: {failed_count} files")

    # List files in R2 to verify
    print(f"\n=== Verifying R2 contents ===")
    r2_files = r2_backend.list_files("")
    print(f"Total files in R2: {len(r2_files)}")
    for f in sorted(r2_files)[:10]:
        print(f"  {f}")
    if len(r2_files) > 10:
        print(f"  ... and {len(r2_files) - 10} more")


if __name__ == "__main__":
    main()
