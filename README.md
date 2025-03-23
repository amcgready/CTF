[![Join us on Discord](https://img.shields.io/badge/Chat-Join%20us%20on%20Discord-7289da?logo=discord&logoColor=white)](https://discord.gg/hdDj4aZTVf)
![GitHub all releases](https://img.shields.io/github/downloads/amcgready/CTF/total)

# CTF
CTF (Capture the Flag or Chrome to Firefox) is a developer tool to quickly port Chrome extensions to Firefox. This script is designed to be run on a Windows machine, other OS support may be added in the future depending on user request. Extensions with additional security, such as official Adobe or Google extensions, can not be converted. If you find an extension that can not be converted, please open a new Issue with the extension ID number so I can keep a log.

# Features
- Quickly attempts to convert Chrome extensions to Firefox extensions
- Proposes potential Firefox alternatives to extensions
- Terminal output saved to rotating log file
- Terminal output color coded for quick error logging

# How to Run
- Clone repo or download main.py script
- Open a terminal window and type 'python main.py' and follow on-screen instructions

Firefox Extension Installation Instructions
=====================================

Due to Firefox's signing requirements, there are several ways to use these extensions:

Option 1: Temporary Installation (Easiest, but only lasts until Firefox restarts)
----------------------------------------------------------------
1. Open Firefox and go to about:debugging
2. Click 'This Firefox'
3. Click 'Load Temporary Add-on...'
4. Browse to the folder for each extension and select the manifest.json file

Option 2: Use Firefox Developer Edition or Nightly
----------------------------------------------------------------
1. Download and install Firefox Developer Edition or Firefox Nightly
2. Go to about:config and set xpinstall.signatures.required to false
3. Then you can install the .xpi files directly

Option 3: Use Firefox ESR
----------------------------------------------------------------
1. Download and install Firefox ESR
2. Go to about:config and set xpinstall.signatures.required to false
3. Then you can install the .xpi files directly

Option 4: Submit to Mozilla for Official Signing
----------------------------------------------------------------
For permanent installation in regular Firefox:
1. Create a developer account at https://addons.mozilla.org
2. Use web-ext tool to package and submit your extension:
   npm install -g web-ext
   cd [extension_folder]
   web-ext lint
   web-ext build
3. Upload the generated .zip file to https://addons.mozilla.org/developers/
4. Wait for Mozilla review and approval

[![Donate](https://img.shields.io/badge/Donate-PayPal-blue.svg)](https://paypal.me/PhtmRaven?country.x=US&locale.x=en_US)
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-💖%20GitHub%20Sponsors-orange?logo=github)](https://github.com/sponsors/amcgready)
