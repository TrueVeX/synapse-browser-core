"""Rebrand a Brave Core checkout as SYNAPSE Browser by HumanForm Studios.

Run after `pnpm run init` and before building:
    python apply_branding.py <chromium src dir>      (brave-core is at <src>/brave)

It changes only brave-core's own branding inputs; Brave's build then copies
them over Chromium as usual. Every step checks that what it expects is there,
so an upstream change makes the script fail loudly instead of half-branding.
"""
import re
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_icons import draw_mark, wordmark  # noqa: E402

HERE = Path(__file__).resolve().parent
SVG = (HERE / "icons" / "product_logo.svg").read_bytes().decode("utf-8").replace("\r\n", "\n")
ICO = HERE / "icons" / "synapse.ico"

BRANDING = {
    "COMPANY_FULLNAME": "HumanForm Studios",
    "COMPANY_SHORTNAME": "HumanForm Studios",
    "PRODUCT_FULLNAME": "SYNAPSE Browser",
    "PRODUCT_SHORTNAME": "SYNAPSE",
    "PRODUCT_INSTALLER_FULLNAME": "SYNAPSE Installer",
    "PRODUCT_INSTALLER_SHORTNAME": "SYNAPSE Installer",
    "COPYRIGHT": "Copyright 2026 HumanForm Studios. Built on Brave and Chromium.",
    "MAC_BUNDLE_ID": "com.humanformstudios.synapse",
}

# Names of outside services that stay as they are.
KEEP = ["Brave Search", "Brave Talk"]
TEXT_RULES = [
    (re.compile(r"Brave Software,? Inc\.?"), "HumanForm Studios"),
    (re.compile(r"Brave Software"), "HumanForm Studios"),
    (re.compile(r"The Brave Authors"), "HumanForm Studios"),
    (re.compile(r"Brave Browser"), "SYNAPSE Browser"),
    (re.compile(r"\bBrave\b"), "SYNAPSE"),
]

INSTALL_MODES = [
    ('L"BraveSoftware"', 'L"HumanFormStudios"'),
    ('L"Brave-Browser-Development"', 'L"SYNAPSE-Browser"'),
    ('L"Brave Development HTML Document"', 'L"SYNAPSE HTML Document"'),
    ('L"Brave Development PDF Document"', 'L"SYNAPSE PDF Document"'),
    ('L"Brave Development"', 'L"SYNAPSE"'),
    ('L"BraveDevelopment"', 'L"SYNAPSEBrowser"'),
    ('L"BraveDevHTM"', 'L"SynapseHTM"'),
    ('L"BraveDevPDF"', 'L"SynapsePDF"'),
    ('"brave-browser-development"', '"synapse-browser"'),
]


def read(f: Path) -> str:
    return f.read_bytes().decode("utf-8")


def write(f: Path, text: str) -> None:
    f.write_bytes(text.encode("utf-8"))  # keeps the file's own line endings


def rebrand_text(text: str) -> str:
    holders = {}
    for i, k in enumerate(KEEP):
        token = f"\x00{i}\x00"
        holders[token] = k
        text = text.replace(k, token)
    for pat, rep in TEXT_RULES:
        text = pat.sub(rep, text)
    for token, k in holders.items():
        text = text.replace(token, k)
    return text


def rebrand_markup(data: str) -> str:
    # Only the text between tags changes: ids, names and attributes stay.
    return re.sub(r">([^<>]+)<", lambda m: ">" + rebrand_text(m.group(1)) + "<", data)


def branding_files(brave: Path) -> int:
    n = 0
    for f in brave.glob("app/theme/*/BRANDING*"):
        lines = []
        for line in read(f).splitlines():
            key = line.split("=", 1)[0]
            lines.append(f"{key}={BRANDING[key]}" if key in BRANDING else line)
        write(f, "\n".join(lines) + "\n")
        n += 1
    assert n >= 2, "BRANDING files not found"
    return n


def logo_for(name: str, size: tuple[int, int]) -> Image.Image:
    w, h = size
    if "name" in name:
        img = wordmark(h, (255, 255, 255, 255) if "white" in name else (20, 20, 20, 255))
        if img.width > w:  # keep inside the original box
            img = img.resize((w, max(1, int(h * w / img.width))), Image.LANCZOS)
        return img
    if "mono" in name:
        return draw_mark(max(w, h), background=False, mono="black").resize((w, h), Image.LANCZOS)
    if "white" in name:
        return draw_mark(max(w, h), background=False, mono="white").resize((w, h), Image.LANCZOS)
    return draw_mark(max(w, h)).resize((w, h), Image.LANCZOS)


def icons(brave: Path) -> int:
    n = 0
    theme = brave / "app" / "theme"
    for f in theme.rglob("product_logo*.png"):
        with Image.open(f) as im:
            size = im.size
        logo_for(f.name, size).save(f)
        n += 1
    for f in theme.rglob("product_logo*.svg"):
        if "animation" not in f.name:
            write(f, SVG)
            n += 1
    for f in (theme / "brave" / "win").glob("*.ico"):
        if f.name not in ("incognito.ico", "placeholder.ico"):
            f.write_bytes(ICO.read_bytes())
            n += 1
    for name in ("Logo.png", "SmallLogo.png"):
        f = theme / "brave" / "win" / "tiles" / name
        if f.exists():
            f.write_bytes((HERE / "icons" / name).read_bytes())
            n += 1
    # Logos used inside Brave's own pages (settings, about, new tab).
    for f in brave.rglob("brave-icon-*-color.svg"):
        write(f, SVG)
        n += 1
    assert n >= 20, f"only {n} logo files replaced"
    return n


def strings(brave: Path) -> int:
    n = 0
    skip = ("test", "node_modules", "third_party", ".git")
    for pattern in ("*.grd", "*.grdp", "*.xtb"):
        for f in brave.rglob(pattern):
            if any(part in skip or part.startswith("test") for part in f.parts):
                continue
            data = read(f)
            new = rebrand_markup(data)
            if new != data:
                write(f, new)
                n += 1
    assert n >= 20, f"only {n} string files changed"
    return n


def install_modes(brave: Path) -> None:
    f = brave / "chromium_src" / "chrome" / "install_static" / "chromium_install_modes.h"
    data = read(f)
    for old, new in INSTALL_MODES:
        assert old in data, f"{old} not found in {f}"
        data = data.replace(old, new)
    write(f, data)


def main() -> None:
    src = Path(sys.argv[1]).resolve()
    brave = src / "brave"
    assert (brave / "package.json").exists(), f"no brave-core at {brave}"
    print("BRANDING files:", branding_files(brave))
    print("logo files:", icons(brave))
    print("string files:", strings(brave))
    install_modes(brave)
    print("install modes: SYNAPSE-Browser under HumanFormStudios")


if __name__ == "__main__":
    main()
