"""Bulk-load knowledge into WhyBot (HydraDB) from the command line.

  python ingest.py --folder ./my_docs              # .md .txt .pdf .csv .json
  python ingest.py --url https://docs.hydradb.com/ # repeatable
  python ingest.py --urls urls.txt                 # one URL per line
  python ingest.py --sample                        # optional starter data
  add --no-wait to skip waiting for graph indexing
"""
import argparse
import logging
import pathlib
import sys

from whybot import hydra
from whybot.config import settings
from whybot.services import knowledge, personas


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", help="folder of your own documents")
    ap.add_argument("--url", action="append", default=[], help="public web page to ingest")
    ap.add_argument("--urls", help="text file with one URL per line")
    ap.add_argument("--sample", action="store_true", help="load optional starter data")
    ap.add_argument("--no-wait", action="store_true", help="don't wait for graph indexing")
    a = ap.parse_args()

    urls = list(a.url)
    if a.urls:
        urls += [l.strip() for l in pathlib.Path(a.urls).read_text().splitlines() if l.strip()]
    if not (a.folder or urls or a.sample):
        ap.error("pass --folder, --url/--urls and/or --sample")
    if settings.mock:
        print("Offline mode (no HYDRA_DB_API_KEY or MOCK_MODE=1): docs are added to the local brain only.")

    ids: list[str] = []
    if a.folder:
        for f in sorted(pathlib.Path(a.folder).rglob("*")):
            if f.is_file() and f.suffix.lower() in knowledge.ALLOWED_EXT:
                try:
                    ids += knowledge.upload(f.name, f.read_bytes())
                    print("✓", f.name)
                except ValueError as e:
                    print("✗", f.name, "-", e)
    for u in urls:
        try:
            ids += knowledge.ingest_url(u)
            print("✓", u)
        except ValueError as e:
            print("✗", u, "-", e)
    if a.sample:
        ids += knowledge.load_sample()
        print("✓ starter data + explicit dependency graph")

    personas.sync_all()
    if ids and not settings.mock and not a.no_wait:
        print("Waiting for indexing (graph answers need 'completed')…")
        hydra.wait_for_indexing(ids)
    print("Done. Run ./start.sh and open http://localhost:3000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
