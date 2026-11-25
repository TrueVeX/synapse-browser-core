"""Remove Brave's lion logo and name from places apply_branding.py does not
reach:  python debrand.py <chromium src dir>

Runs on every build stage, after Brave's node_modules are reinstalled (they are
reinstalled each stage, which would bring Brave's original icons back). Files
are only rewritten when they change, so an unchanged tree causes no rebuild.

  - Shields button in the address bar: lion vector icons and PNGs -> SYNAPSE mark
  - Welcome page (first run): 3D lion image -> SYNAPSE mark
  - Brave's Leo icon set: Brave and Brave Search lion icons -> SYNAPSE mark
    (Brave Search stays the default search engine)
  - About page: "Brave 1.100.x" -> "SYNAPSE 1.100.x"
  - New tab page: the Brave Talk card is off by default
"""
import io
import re
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_icons import draw_mark  # noqa: E402

SVG = (HERE / "icons" / "product_logo.svg").read_bytes().decode("utf-8").replace("\r\n", "\n")

# SYNAPSE mark on a 32x32 grid (same geometry as icons/product_logo.svg).
LINES = [(16, 11.6, 16, 6.4), (19.81, 13.8, 24.31, 11.2), (19.81, 18.2, 24.31, 20.8),
         (16, 20.4, 16, 25.6), (12.19, 18.2, 7.69, 20.8), (12.19, 13.8, 7.69, 11.2)]
CIRCLES = [(16, 3.8, 2.6), (26.57, 9.9, 2.2), (26.57, 22.1, 2.6), (16, 28.2, 2.2),
           (5.43, 22.1, 2.6), (5.43, 9.9, 2.2), (16, 16, 3.4)]

MONO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<g fill="currentColor" stroke="currentColor" stroke-width="2.4" stroke-linecap="round">'
    + "".join(f'<line x1="{a}" y1="{b}" x2="{c}" y2="{d}"/>' for a, b, c, d in LINES)
    + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" stroke="none"/>' for x, y, r in CIRCLES)
    + "</g></svg>\n")


def num(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v}f"


def vector_icon(argb: tuple[int, int, int, int] | None = None) -> str:
    """Chromium .icon (vector icon) source for the SYNAPSE mark. Without a color
    the icon takes the color the browser asks for (like Brave's monochrome icons)."""
    color = [f"PATH_COLOR_ARGB, {', '.join(f'0x{c:02X}' for c in argb)},"] if argb else []
    out = ["CANVAS_DIMENSIONS, 32,"] + color + ["STROKE, 2.4f,"]
    for x1, y1, x2, y2 in LINES:
        out += [f"MOVE_TO, {num(x1)}, {num(y1)},", f"LINE_TO, {num(x2)}, {num(y2)},"]
    out += ["NEW_PATH,"] + color
    out += [f"CIRCLE, {num(x)}, {num(y)}, {num(r)}," for x, y, r in CIRCLES]
    return "\n".join(out) + "\n"


def read(f: Path) -> str:
    return f.read_bytes().decode("utf-8")


def write_if_changed(f: Path, data: bytes) -> bool:
    if f.read_bytes() == data:
        return False
    f.write_bytes(data)
    return True


def image_bytes(img: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    img.save(buf, fmt, **({"lossless": True} if fmt == "WEBP" else {}))
    return buf.getvalue()


def faded(img: Image.Image) -> Image.Image:
    gray = img.convert("LA").convert("RGBA")
    gray.putalpha(gray.getchannel("A").point(lambda a: a * 45 // 100))
    return gray


# Raster images: the file stays, only its picture changes. Generated images are
# compared by content, so a second run changes nothing.
def raster(f: Path, make) -> bool:
    with Image.open(f) as im:
        size, fmt = im.size, im.format
    return write_if_changed(f, image_bytes(make(size), fmt))


def shields_and_welcome(brave: Path) -> list[str]:
    done = []
    shields = brave / "components" / "brave_shields" / "resources"
    for name, make in (("icon.png", lambda s: draw_mark(max(s))),
                       ("icon-off.png", lambda s: faded(draw_mark(max(s))))):
        f = shields / name
        assert f.exists(), f"{f} not found"
        done.append(f"{name}: {'replaced' if raster(f, make) else 'already SYNAPSE'}")
    assets = brave / "components" / "brave_welcome_ui" / "assets"
    # Welcome page artwork: Brave's purple sky, hill and pyramids are swapped for
    # the black-and-grey versions Brave ships for its "Origin" edition, which
    # match SYNAPSE's black/white palette.
    n = 0
    for name in ("background@2x", "sky", "hill", "pyramid"):
        dark = assets / f"{name}_origin.webp"
        assert dark.exists(), f"{dark} not found"
        n += write_if_changed(assets / f"{name}.webp", dark.read_bytes())
    done.append(f"welcome artwork: {n} images switched to black and grey")
    f = assets / "brave_logo_3d@2x.webp"
    assert f.exists(), f"{f} not found"
    # The white SYNAPSE mark, centered where the lion was.
    def welcome(size):
        w, h = size
        side = min(w, h) * 3 // 4
        canvas = Image.new("RGBA", size, (0, 0, 0, 0))
        canvas.paste(draw_mark(side, background=False, mono="white"), ((w - side) // 2, (h - side) // 2))
        return canvas
    done.append(f"welcome logo: {'replaced' if raster(f, welcome) else 'already SYNAPSE'}")
    return done


def leo_icons(brave: Path) -> list[str]:
    leo = brave / "node_modules" / "@brave" / "leo"
    assert leo.is_dir(), f"{leo} not found (run after pnpm install)"
    n = 0
    # Lion icons: Brave's own logo, and Brave Search's (shown in the new tab
    # page search box; Brave Search stays the default engine, with our mark).
    # Vector icons drawn by the browser window (Shields button, menus).
    skia = leo / "icons-skia"
    for name in ("leo_brave_icon_only_face.icon", "leo_brave_icon_only_face_disabled.icon",
                 "leo_brave_icon_monochrome.icon"):
        assert (skia / name).exists(), f"{skia / name} not found"
    icons = [f for pat in ("leo_brave_icon*.icon", "leo_social_brave*.icon", "leo_brave_search*.icon")
             for f in skia.glob(pat)]
    for f in icons:
        argb = (0x73, 0x80, 0x80, 0x80) if "disabled" in f.name else None
        n += write_if_changed(f, vector_icon(argb).encode("utf-8"))
    # Icons used inside Brave's pages.
    svgs = [f for pat in ("brave-icon*.svg", "social-brave*.svg", "brave-search*.svg")
            for f in (leo / "icons").glob(pat)]
    names = {f.name for f in svgs}
    for name in ("brave-icon-release-color.svg", "social-brave-release-favicon-fullheight-color.svg"):
        assert name in names, f"{name} not found in {leo / 'icons'}"
    for f in svgs:
        n += write_if_changed(f, (SVG if "color" in f.name else MONO_SVG).encode("utf-8"))
    return [f"Leo lion icons: {n} replaced ({len(svgs) + len(icons)} checked)"]


def about_version(brave: Path) -> str:
    f = brave / "browser" / "resources" / "settings" / "br" / "about_page.ts"
    data = read(f)
    old, new = "`Brave ${braveVersion} ${build}`", "`SYNAPSE ${braveVersion} ${build}`"
    if new in data:
        return "about version: already SYNAPSE"
    assert data.count(old) == 1, f"{old} not found in {f}"
    write_if_changed(f, data.replace(old, new).encode("utf-8"))
    return "about version: SYNAPSE"


def talk_card_off(brave: Path) -> str:
    f = brave / "browser" / "brave_profile_prefs.cc"
    data = read(f)
    pat = re.compile(r"(kNewTabPageShowBraveTalk,\s*)true(\);)")
    if not pat.search(data):
        assert re.search(r"kNewTabPageShowBraveTalk,\s*false\);", data), f"Brave Talk pref not found in {f}"
        return "Brave Talk card: already off"
    write_if_changed(f, pat.sub(r"\1false\2", data, count=1).encode("utf-8"))
    return "Brave Talk card: off by default"


def search_favicon(brave: Path) -> str:
    # Brave Search stays the default engine. Its favicon (address bar
    # suggestions, search engine list) is downloaded from this URL; point it at
    # the SYNAPSE logo on the SYNAPSE site instead of Brave's lion.
    f = brave / "components" / "search_engines" / "brave_prepopulated_engines.cc"
    data = read(f)
    old, new = "https://cdn.search.brave.com/serp/favicon.ico", "https://synapse-browser.vercel.app/apple-icon.png"
    if new in data:
        return "Brave Search favicon: already SYNAPSE"
    assert data.count(old) == 1, f"{old} not found in {f}"
    write_if_changed(f, data.replace(old, new).encode("utf-8"))
    return "Brave Search favicon: SYNAPSE logo"


# Exact text swaps: (file under brave/, old, new). Each old text must be found
# (or already replaced), so an upstream change fails loudly.
SWAPS = [
    # Internal pages show synapse://settings etc. instead of brave://settings.
    ("components/constants/url_constants.h",
     'kBraveUIScheme[] = "brave";', 'kBraveUIScheme[] = "synapse";'),
    ("chromium_src/content/public/common/url_constants.h",
     'kBraveUIScheme[] = "brave";', 'kBraveUIScheme[] = "synapse";'),
    ("browser/ui/webui/brave_web_ui_controller_factory.cc",
     'url.SchemeIs("brave")', 'url.SchemeIs("synapse")'),
    ("chromium_src/components/webui/chrome_urls/resources/app.html.ts.lit_mangler.ts",
     '/chrome:/, "brave:"', '/chrome:/, "synapse:"'),
    # "List of Brave URLs" page heading.
    ("chromium_src/components/webui/chrome_urls/resources/app.html.ts.lit_mangler.ts",
     "'List of Brave URLs'", "'List of SYNAPSE URLs'"),
    ("components/webui/about_ui.cc",
     '"List of Brave URLs"', '"List of SYNAPSE URLs"'),
    # What websites can see: the Client Hints brand and the WebGL
    # fingerprinting-protection value.
    ("chromium_src/components/embedder_support/user_agent_utils.cc",
     'kBraveBrandNameForCHUA[] = "Brave";', 'kBraveBrandNameForCHUA[] = "SYNAPSE";'),
    ("chromium_src/third_party/blink/renderer/modules/webgl/webgl_rendering_context_base.cc",
     'blink::String("Brave")', 'blink::String("SYNAPSE")'),
    # Windows policy registry key: ...\Policies\HumanFormStudios\SYNAPSE.
    ("chromium_src/chrome/install_static/user_data_dir.cc",
     'path->append(L"Brave");', 'path->append(L"SYNAPSE");'),
    # Chrome Web Store button ("Add to Chrome" -> "Add to SYNAPSE").
    ("components/brave_extension/extension/brave_extension/webstore.ts",
     "text.replace('Chrome', 'Brave')", "text.replace('Chrome', 'SYNAPSE')"),
    # Screen-reader name of the new tab page search boxes.
    ("components/brave_new_tab_ui/components/default/searchPromotion/searchBox.tsx",
     'aria-label="Brave"', 'aria-label="Search"'),
    ("components/brave_private_new_tab_ui/resources/page/components/search-box/index.tsx",
     'aria-label="Brave"', 'aria-label="Search"'),
    ("components/brave_ads/browser/resources/components/resources.tsx",
     "delivered via Brave's component updater", "delivered via SYNAPSE's component updater"),
]


def swaps(brave: Path) -> str:
    n = 0
    for rel, old, new in SWAPS:
        f = brave / rel
        data = read(f)
        if old in data:
            n += write_if_changed(f, data.replace(old, new).encode("utf-8"))
        else:
            assert new in data, f"{old!r} not found in {f}"
    return f"Brave names and brave: scheme: {n} of {len(SWAPS)} swaps made"


# brave:// links written into Brave's code and translations -> synapse://, so
# links keep working with the renamed scheme. Tests and other platforms are
# left alone.
SCHEME_EXTS = {".cc", ".h", ".mm", ".ts", ".tsx", ".js", ".html", ".grd", ".grdp", ".xtb", ".json"}
SKIP_DIRS = {"node_modules", ".git", "test", "tests", "ios", "android", "build", "script", "third_party",
             "storybook", "stories"}


def candidates(brave: Path):
    """Files that may contain brave:// links. git grep is fast; walking the
    tree is the fallback when brave/ is not a git checkout."""
    import os
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(brave), "grep", "-l", "-I", "-F", "brave://"],
                             capture_output=True, check=True).stdout.decode("utf-8")
        for line in out.splitlines():
            yield brave / line
        return
    except (OSError, subprocess.CalledProcessError):
        pass
    for root, dirs, files in os.walk(brave):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            yield Path(root) / name


def scheme_links(brave: Path) -> str:
    changed = seen = 0
    for f in candidates(brave):
        rel = f.relative_to(brave)
        if (f.suffix not in SCHEME_EXTS or "test" in f.name
                or any(p in SKIP_DIRS or p.startswith("test") for p in rel.parts[:-1])):
            continue
        data = f.read_bytes()
        if b"brave://" not in data:
            continue
        seen += 1
        changed += write_if_changed(f, data.replace(b"brave://", b"synapse://"))
    return f"brave:// links: {changed} of {seen} files changed"


def main() -> None:
    src = Path(sys.argv[1]).resolve()
    brave = src / "brave"
    assert (brave / "package.json").exists(), f"no brave-core at {brave}"
    for line in shields_and_welcome(brave) + leo_icons(brave) + [
            about_version(brave), talk_card_off(brave), search_favicon(brave),
            swaps(brave), scheme_links(brave)]:
        print(line)


if __name__ == "__main__":
    main()
