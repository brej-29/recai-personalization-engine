import argparse
import os
from pathlib import Path
from zipfile import ZipFile

import requests
from tqdm import tqdm

DEFAULT_URL = "https://files.grouplens.org/datasets/movielens/ml-1m.zip"


def download_movielens_1m(data_dir: Path) -> None:
    raw_dir = data_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    zip_path = raw_dir / "ml-1m.zip"
    target_dir = raw_dir / "ml-1m"

    if target_dir.exists():
        print(f"[INFO] MovieLens 1M already present at {target_dir}")
        return

    if not zip_path.exists():
        print(f"[INFO] Downloading MovieLens 1M from {DEFAULT_URL}")
        try:
            resp = requests.get(DEFAULT_URL, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(zip_path, "wb") as f, tqdm(
                total=total, unit="B", unit_scale=True, desc="ml-1m.zip"
            ) as pbar:
                for chunk in resp.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        except Exception as exc:
            print("[ERROR] Failed to download MovieLens 1M:", exc)
            print(
                f"[ACTION] Please download the dataset manually from {DEFAULT_URL} "
                f"and place the zip file at: {zip_path}"
            )
            return

    print(f"[INFO] Extracting {zip_path} to {raw_dir}")
    try:
        with ZipFile(zip_path, "r") as zf:
            zf.extractall(raw_dir)
    except Exception as exc:
        print("[ERROR] Failed to extract MovieLens 1M:", exc)
        print(
            f"[ACTION] If the zip is corrupted, delete {zip_path} and try again, "
            "or manually extract it into data/raw/ml-1m/"
        )
        return

    if not target_dir.exists():
        print(
            "[WARNING] Extraction finished but ml-1m directory was not found. "
            f"Ensure that data is available under {target_dir}."
        )
    else:
        print(f"[OK] MovieLens 1M available under {target_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MovieLens 1M dataset")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(os.getenv("DATA_DIR", "data")),
        help="Base data directory",
    )
    args = parser.parse_args()
    download_movielens_1m(args.data_dir)


if __name__ == "__main__":
    main()