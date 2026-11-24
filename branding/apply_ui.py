"""Apply the SYNAPSE desktop UI (from the Brave Browser UI Kit (Community)) to a
Brave Core checkout:  python apply_ui.py <chromium src dir>

The kit uses Brave's own desktop layout (tab strip, toolbar, omnibox, Shields,
bookmarks bar, menus), so the layout stays. What it sets is the kit's colors
and that the bookmarks bar is always shown:

                 window frame /    active tab, toolbar,   address bar
                 inactive tabs     bookmarks bar
  dark theme     #0D0D17           #303443                #181A21
  light theme    #D5D9DC           #F3F3F3                #FFFFFF
  accent (prominent buttons such as "Done"): #FB542B

The colors apply to normal windows with the default theme. Private and Tor
windows and themes the user installs keep their own colors.

Safe to run on every build stage: files are only rewritten when they change,
so an unchanged tree causes no rebuild.
"""
import sys
from pathlib import Path

MARK = "SYNAPSE UI kit colors"

MIXER = r'''
// SYNAPSE UI kit colors (added by synapse-browser-core/branding/apply_ui.py).
// Runs after every other mixer (see AddNativeChromeColorMixer below), so the
// kit's colors win over Chromium's and Brave's defaults.
#include "chrome/browser/ui/color/native_chrome_color_mixer.h"
#include "chrome/browser/ui/color/chrome_color_id.h"
#include "third_party/skia/include/core/SkColor.h"
#include "ui/color/color_id.h"
#include "ui/color/color_mixer.h"
#include "ui/color/color_provider.h"
#include "ui/color/color_provider_key.h"

namespace {

void AddSynapseKitColorMixer(ui::ColorProvider* provider,
                             const ui::ColorProviderKey& key) {
  // Private/Tor windows (Brave theme suppliers) and installed themes keep
  // their own colors.
  if (key.custom_theme || key.app_controller) {
    return;
  }
  const bool dark = key.color_mode == ui::ColorProviderKey::ColorMode::kDark;
  const SkColor frame =
      dark ? SkColorSetRGB(0x0D, 0x0D, 0x17) : SkColorSetRGB(0xD5, 0xD9, 0xDC);
  const SkColor toolbar =
      dark ? SkColorSetRGB(0x30, 0x34, 0x43) : SkColorSetRGB(0xF3, 0xF3, 0xF3);
  const SkColor omnibox =
      dark ? SkColorSetRGB(0x18, 0x1A, 0x21) : SkColorSetRGB(0xFF, 0xFF, 0xFF);
  const SkColor accent = SkColorSetRGB(0xFB, 0x54, 0x2B);

  ui::ColorMixer& mixer = provider->AddPostprocessingMixer();
  mixer[ui::kColorFrameActive] = {frame};
  mixer[ui::kColorFrameInactive] = {frame};
  mixer[kColorToolbar] = {toolbar};
  mixer[kColorTabBackgroundActiveFrameActive] = {toolbar};
  mixer[kColorTabBackgroundActiveFrameInactive] = {toolbar};
  mixer[kColorTabBackgroundInactiveFrameActive] = {frame};
  mixer[kColorTabBackgroundInactiveFrameInactive] = {frame};
  mixer[kColorBookmarkBarBackground] = {toolbar};
  mixer[kColorLocationBarBackground] = {omnibox};
  mixer[kColorLocationBarBackgroundHovered] = {omnibox};
  mixer[ui::kColorButtonBackgroundProminent] = {accent};
  mixer[ui::kColorButtonForegroundProminent] = {SK_ColorWHITE};
}

}  // namespace

#define AddNativeChromeColorMixer(provider, key) \
  AddNativeChromeColorMixer(provider, key);      \
  AddSynapseKitColorMixer(provider, key)
'''

INCLUDE = "#include <chrome/browser/ui/color/chrome_color_mixers.cc>"


def read(f: Path) -> str:
    return f.read_bytes().decode("utf-8")


def write_if_changed(f: Path, text: str) -> bool:
    if read(f) == text:
        return False
    f.write_bytes(text.encode("utf-8"))
    return True


def colors(src: Path) -> str:
    f = src / "brave" / "chromium_src" / "chrome" / "browser" / "ui" / "color" / "chrome_color_mixers.cc"
    data = read(f)
    if MARK in data:
        return "colors: already applied"
    assert data.count(INCLUDE) == 1, f"{INCLUDE} not found in {f}"
    nl = "\r\n" if "\r\n" in data else "\n"
    block = MIXER.replace("\n", nl)
    data = data.replace(INCLUDE, block.lstrip(nl) + nl + INCLUDE + nl + "#undef AddNativeChromeColorMixer", 1)
    write_if_changed(f, data)
    return "colors: added"


def bookmarks_bar(src: Path) -> str:
    # Chromium registers this pref after Brave's default overrides run, so the
    # default is changed where it is registered.
    f = src / "components" / "bookmarks" / "browser" / "bookmark_utils.cc"
    data = read(f)
    new = data.replace("prefs::kShowBookmarkBar, false,", "prefs::kShowBookmarkBar, true,")
    # Newer three-way setting (always / only on the new tab page / never).
    new = new.replace("static_cast<int>(BookmarkBarVisibilityState::kOnlyShowOnNtp),",
                      "static_cast<int>(BookmarkBarVisibilityState::kAlwaysShow),")
    assert "prefs::kShowBookmarkBar, true," in new, f"kShowBookmarkBar default not found in {f}"
    if "kBookmarkBarVisibilityState" in new:
        assert "BookmarkBarVisibilityState::kAlwaysShow)," in new, f"visibility default not found in {f}"
    return "bookmarks bar: always shown" if write_if_changed(f, new) else "bookmarks bar: already always shown"


def main() -> None:
    src = Path(sys.argv[1]).resolve()
    assert (src / "brave" / "package.json").exists(), f"no brave-core at {src / 'brave'}"
    print(colors(src))
    print(bookmarks_bar(src))


if __name__ == "__main__":
    main()
