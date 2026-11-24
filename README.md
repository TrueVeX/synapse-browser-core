# SYNAPSE Browser (Brave Core)

SYNAPSE Browser by **HumanForm Studios** (Revoori Ashwath Reddy), built on
[Brave Core](https://github.com/brave/brave-core) and Chromium.

This repo holds only what makes SYNAPSE different from Brave: the branding,
the build settings and the GitHub build. Brave Core and Chromium are
downloaded during the build.

## What SYNAPSE changes
- **Name and logo:** SYNAPSE Browser by HumanForm Studios everywhere Brave shows its
  name or lion (`branding/apply_branding.py`, icons drawn by `branding/make_icons.py`).
- **Desktop UI from the Brave Browser UI Kit (Community):** the kit's dark and light colors for the
  window frame, tabs, toolbar, address bar and bookmarks bar, orange accent buttons, and the
  bookmarks bar shown on every page (`branding/apply_ui.py`).
- **Installs separately from Brave:** its own folder (`%LOCALAPPDATA%\HumanFormStudios\SYNAPSE-Browser`),
  its own registry names and its own `synapse-browser:` link scheme.
- **No Brave account services:** Rewards, Wallet, VPN, Leo AI, News and Tor are left out of the build.
  Brave Shields (ad and tracker blocking) stays.
- **No Brave updater:** the build is not an "official" Brave build, so it never contacts Brave's update servers.

Brave Core version: see [`BRAVE_VERSION`](BRAVE_VERSION).

## Building (Windows x64)
A full build takes far longer than the 6 hours a free GitHub runner allows, so
`.github/workflows/build-windows.yml` runs it as a chain of up to 12 stages.
Each stage compiles for about 4 hours, saves the build folder as an artifact,
and the next stage carries on. Start it from Actions → "SYNAPSE Windows build" → Run workflow:

    gh workflow run build-windows.yml --repo TrueVeX/synapse-browser-core

To continue from a failed run's last saved stage (kept for 2 days) instead of starting over:

    gh workflow run build-windows.yml --repo TrueVeX/synapse-browser-core -f resume_from=<run id>

The finished installer and portable zip are uploaded as the `synapse-windows` artifact.
After changing `build/gen_workflow.py`, run `python build/gen_workflow.py`.

## License
SYNAPSE's own files and Brave Core are under the [Mozilla Public License 2.0](LICENSE).
Chromium is under a BSD-style license. SYNAPSE is not affiliated with or endorsed
by Brave Software. Brave is a trademark of Brave Software, Inc.
