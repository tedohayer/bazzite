#!/usr/bin/env python3
"""Benchmark how generate_release gets package lists: raw SBOM, zstd SBOM, or a
small per-image package file."""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "workflows"))
import changelog  # noqa: E402

UPSTREAM = "ghcr.io/ublue-os/"
LEVELS = [3, 19]
SBOM_TYPE = "application/vnd.spdx+json"


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, capture_output=True, **kw)


def clock():
    return time.monotonic()


def pairs(tags):
    for tag in tags:
        for img in changelog.IMAGES:
            yield img, tag


def bench_ref(owner, img, tag, variant):
    return f"ghcr.io/{owner}/changelog-bench:{img}-{tag}-{variant}"


def push(ref, workdir, name):
    t = clock()
    sh(["oras", "push", "--artifact-type", SBOM_TYPE, ref, f"{name}:{SBOM_TYPE}"], cwd=workdir)
    return clock() - t


def cmd_prep(args):
    out = Path(args.out)
    rows = []
    for img, tag in pairs(args.tags):
        print(f"prep {img}:{tag}", flush=True)
        row = {"image": img, "tag": tag}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            digest = changelog.get_image_digest(UPSTREAM + img, tag)
            disc = json.loads(sh(["oras", "discover", "--format", "json", f"{UPSTREAM}{img}@{digest}"]).stdout)
            sbom_digest = next(
                r["digest"] for r in disc.get("referrers", []) if SBOM_TYPE in r.get("artifactType", "")
            )
            t = clock()
            sh(["oras", "pull", f"{UPSTREAM}{img}@{sbom_digest}"], cwd=tmp)
            row["upstream_pull_s"] = clock() - t
            raw = next(p for p in tmp.iterdir() if p.suffix == ".json")
            raw = raw.rename(tmp / "sbom.json")
            row["raw_bytes"] = raw.stat().st_size

            t = clock()
            pkgs = changelog.parse_sbom_packages(json.loads(raw.read_bytes()))
            dest = out / f"pkgs-{tag}" / f"packages-{img}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(pkgs, sort_keys=True))
            row["pkgfile_extract_s"] = clock() - t
            row["pkgfile_bytes"] = dest.stat().st_size

            row["raw_push_s"] = push(bench_ref(args.owner, img, tag, "raw"), tmp, "sbom.json")
            for level in LEVELS:
                zst = tmp / "sbom.json.zst"
                t = clock()
                sh(["zstd", "-q", "-f", f"-{level}", "-T0", str(raw), "-o", str(zst)])
                row[f"zst{level}_compress_s"] = clock() - t
                row[f"zst{level}_bytes"] = zst.stat().st_size
                row[f"zst{level}_push_s"] = push(bench_ref(args.owner, img, tag, f"zst{level}"), tmp, zst.name)
                zst.unlink()
        rows.append(row)
        print(json.dumps(row), flush=True)
    (out / "prep.json").write_text(json.dumps(rows, indent=1))


def cmd_fetch(args):
    rows = []
    start = clock()
    for img, tag in pairs(args.tags):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            t = clock()
            sh(["oras", "pull", bench_ref(args.owner, img, tag, args.variant)], cwd=tmp)
            pull_s = clock() - t
            f = next(tmp.iterdir())
            t = clock()
            if f.suffix == ".zst":
                data = sh(["zstd", "-d", str(f), "--stdout"]).stdout
            else:
                data = f.read_bytes()
            pkgs = changelog.parse_sbom_packages(json.loads(data))
            rows.append({"image": img, "tag": tag, "pull_s": pull_s, "decode_s": clock() - t, "packages": len(pkgs)})
    result = {
        "variant": args.variant,
        "total_s": clock() - start,
        "pull_s": sum(r["pull_s"] for r in rows),
        "decode_s": sum(r["decode_s"] for r in rows),
        "rows": rows,
    }
    Path(args.result).write_text(json.dumps(result, indent=1))
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}))


def cmd_pkgfile(args):
    t = clock()
    count = 0
    for d in args.dirs:
        for f in sorted(Path(d).glob("packages-*.json")):
            count += len(json.loads(f.read_text()))
    load_s = clock() - t
    result = {"variant": "pkgfile", "load_s": load_s, "packages": count, "download_s": args.download_s}
    Path(args.result).write_text(json.dumps(result, indent=1))
    print(json.dumps(result))


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(required=True)

    prep = sub.add_parser("prep")
    prep.add_argument("--owner", required=True)
    prep.add_argument("--out", required=True)
    prep.add_argument("--tags", nargs="+", required=True)
    prep.set_defaults(func=cmd_prep)

    fetch = sub.add_parser("fetch")
    fetch.add_argument("--owner", required=True)
    fetch.add_argument("--variant", required=True, choices=["raw"] + [f"zst{lvl}" for lvl in LEVELS])
    fetch.add_argument("--tags", nargs="+", required=True)
    fetch.add_argument("--result", required=True)
    fetch.set_defaults(func=cmd_fetch)

    pkgfile = sub.add_parser("pkgfile")
    pkgfile.add_argument("--dirs", nargs="+", required=True)
    pkgfile.add_argument("--download-s", type=float, required=True)
    pkgfile.add_argument("--result", required=True)
    pkgfile.set_defaults(func=cmd_pkgfile)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
