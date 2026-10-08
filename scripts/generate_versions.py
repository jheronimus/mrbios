import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from parse_import import parse_bios_image


def generate_file_versions():
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bios_root = os.path.join(repo_root, "bios", "mrbios")
    data_root = os.path.join(repo_root, "data", "mrbios")
    output_path = os.path.join(data_root, "versions.json")

    # 1. Parse base versions from binary headers or path
    raw_vers = {}
    for f in glob.glob(os.path.join(bios_root, "**"), recursive=True):
        if f.endswith((".BIN", ".BIO", ".bin", ".bio")):
            rel = os.path.relpath(f, repo_root).replace("\\", "/")
            try:
                with open(f, "rb") as fp:
                    info = parse_bios_image(fp.read())
                    if info and info.get("version"):
                        raw_vers[rel] = info["version"].lstrip("Vv")
            except OSError:
                pass

            if rel not in raw_vers:
                m = re.findall(r"/([0-9]+\.[0-9]+[A-Za-z0-9]*)/", rel)
                if m:
                    raw_vers[rel] = m[-1]

    # 2. Fill unmapped files from row-level "Versions found"
    for yf in glob.glob(os.path.join(data_root, "*.yml")):
        with open(yf, encoding="utf-8") as fp:
            entries = fp.read().split("\n- ")

        for e in entries:
            files = re.findall(r"^\s+-\s+(bios/mrbios/[^\n]+)", e, re.MULTILINE)
            if not files:
                continue

            vf_m = re.search(r"Versions found:\s*['\"]?([^'\"]*?)['\"]?\s*\n", e)
            vf = vf_m.group(1).strip() if vf_m else ""

            for fl in files:
                if fl not in raw_vers and vf and "," not in vf:
                    raw_vers[fl] = vf

    # 3. Generate concise, disambiguated labels
    labels = {}
    for fl, v in raw_vers.items():
        base = os.path.basename(fl)
        stem, ext = os.path.splitext(base)
        ext = ext.lstrip(".").upper()
        parent = os.path.basename(os.path.dirname(fl))

        if "/SHAREWARE/" in fl:
            if re.match(r"^[0-9]+\.[0-9]+", parent):
                labels[fl] = parent
            else:
                labels[fl] = f"{v} ({parent})" if v else parent
        elif ext == "BIO":
            labels[fl] = f"{v} (BIO)" if v else "BIO"
        elif "27C512" in stem:
            labels[fl] = f"{v} (27C512)" if v else "27C512"
        elif stem.endswith("_HI"):
            labels[fl] = f"{v} (HI)" if v else "HI"
        elif stem.endswith("_LO"):
            labels[fl] = f"{v} (LO)" if v else "LO"
        else:
            bio_sibling = os.path.splitext(os.path.join(repo_root, fl))[0] + ".BIO"
            if os.path.exists(bio_sibling):
                labels[fl] = f"{v} (BIN)" if v else "BIN"
            else:
                labels[fl] = v if v else base

    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(labels, out, indent=2, sort_keys=True)

    print(f"Generated {len(labels)} file version labels in {output_path}")


if __name__ == "__main__":
    generate_file_versions()
