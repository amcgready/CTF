import os
import json
import shutil
import platform

def get_browser_profiles(browser):
    """Retrieve available profiles for the specified browser."""
    user_home = os.path.expanduser("~")
    system_platform = platform.system().lower()
    profiles = []

    if browser == "chrome":
        if system_platform == "windows":
            base_path = os.path.join(user_home, "AppData", "Local", "Google", "Chrome", "User Data")
        elif system_platform == "linux":
            base_path = os.path.join(user_home, ".config", "google-chrome")
        else:
            print("Unsupported operating system.")
            return []
    elif browser == "firefox":
        if system_platform == "windows":
            base_path = os.path.join(user_home, "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")
        elif system_platform == "linux":
            base_path = os.path.join(user_home, ".mozilla", "firefox")
        else:
            print("Unsupported operating system.")
            return []
    else:
        print("Unsupported browser.")
        return []

    if os.path.exists(base_path):
        for item in os.listdir(base_path):
            if item == "Default" or item.startswith("Profile "):
                profiles.append(os.path.join(base_path, item))
    else:
        print(f"User data path '{base_path}' does not exist.")
        return []

    return profiles

def get_extension_name(manifest, ext_id, ext_dir):
    """Extract proper extension name from manifest, handling localization if needed."""
    name = manifest.get("name", ext_id)
    
    # Check if the name is a message placeholder
    if isinstance(name, str) and name.startswith("__MSG_") and name.endswith("__"):
        # Extract the message key
        msg_key = name[6:-2]  # Remove __MSG_ prefix and __ suffix
        
        # Look for messages in _locales directory
        locales_dir = os.path.join(ext_dir, "_locales")
        if os.path.exists(locales_dir):
            # Try default locale (en)
            for locale in ["en", "en_US"]:
                locale_path = os.path.join(locales_dir, locale, "messages.json")
                if os.path.exists(locale_path):
                    try:
                        with open(locale_path, "r", encoding="utf-8") as locale_file:
                            messages = json.load(locale_file)
                            if msg_key in messages:
                                return messages[msg_key].get("message", name)
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"Error reading locale file: {e}")
            
            # If en/en_US not found, try any available locale
            available_locales = [d for d in os.listdir(locales_dir) if os.path.isdir(os.path.join(locales_dir, d))]
            if available_locales:
                locale_path = os.path.join(locales_dir, available_locales[0], "messages.json")
                try:
                    with open(locale_path, "r", encoding="utf-8") as locale_file:
                        messages = json.load(locale_file)
                        if msg_key in messages:
                            return messages[msg_key].get("message", name)
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading locale file: {e}")
                    
        # If we reach here, we couldn't extract the name from localization files
        return f"Unknown Extension ({ext_id})"
    
    return name

def get_extensions_from_profile(profile_path, browser):
    """Fetch installed extensions for a given profile."""
    extensions = []
    if browser == "chrome":
        ext_path = os.path.join(profile_path, "Extensions")
    elif browser == "firefox":
        ext_path = os.path.join(profile_path, "extensions")

    print(f"Looking for extensions in: {ext_path}")  # Debug print

    if os.path.exists(ext_path):
        if browser == "chrome":
            # Chrome stores extensions as ext_id/version_number/manifest.json
            for ext_id in os.listdir(ext_path):
                ext_dir = os.path.join(ext_path, ext_id)
                if os.path.isdir(ext_dir):
                    # Get the latest version directory (highest version number)
                    versions = [v for v in os.listdir(ext_dir) if os.path.isdir(os.path.join(ext_dir, v))]
                    if versions:
                        latest_version = sorted(versions)[-1]  # Use the highest version number
                        version_dir = os.path.join(ext_dir, latest_version)
                        manifest_path = os.path.join(version_dir, "manifest.json")
                        
                        if os.path.exists(manifest_path):
                            try:
                                with open(manifest_path, "r", encoding="utf-8") as file:
                                    manifest = json.load(file)
                                    ext_name = get_extension_name(manifest, ext_id, version_dir)
                                    extensions.append((ext_id, ext_name))
                            except json.JSONDecodeError as e:
                                print(f"Error decoding JSON for {ext_id}: {e}")
                    else:
                        print(f"No version folders found for extension: {ext_id}")
        elif browser == "firefox":
            # Keep existing Firefox code but use the new get_extension_name function
            for folder in os.listdir(ext_path):
                manifest_path = os.path.join(ext_path, folder, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as file:
                            manifest = json.load(file)
                            ext_dir = os.path.join(ext_path, folder)
                            ext_name = get_extension_name(manifest, folder, ext_dir)
                            if ext_name:
                                extensions.append((folder, ext_name))
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}")
    else:
        print(f"Extensions path '{ext_path}' does not exist in profile '{profile_path}'.")

    return extensions

def convert_extension(extension_id, selected_profile, target_browser, browser):
    """Convert a browser extension to the desired browser format."""
    if target_browser not in ["chrome", "edge", "firefox"]:
        print("Invalid target browser.")
        return
    
    # Find the extension folder based on browser
    if browser == "chrome":
        ext_path = os.path.join(selected_profile, "Extensions", extension_id)
        
        # Find latest version folder
        if os.path.exists(ext_path):
            versions = [v for v in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, v))]
            if not versions:
                print(f"No version folders found for extension: {extension_id}")
                return
            
            latest_version = sorted(versions)[-1]
            extension_folder = os.path.join(ext_path, latest_version)
        else:
            print(f"Extension folder not found: {ext_path}")
            return
    elif browser == "firefox":
        extension_folder = os.path.join(selected_profile, "extensions", extension_id)
    else:
        print("Unsupported source browser.")
        return

    manifest_path = os.path.join(extension_folder, "manifest.json")
    if not os.path.exists(manifest_path):
        print("Manifest file not found in", extension_folder)
        return

    with open(manifest_path, "r", encoding="utf-8") as file:
        manifest = json.load(file)
        ext_name = get_extension_name(manifest, extension_id, extension_folder)

    # Create safe folder name from extension name
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in ext_name).strip()
    
    if target_browser == "firefox":
        manifest["browser_specific_settings"] = {
            "gecko": {"id": f"{safe_name.lower().replace(' ', '_')}@firefox"}
        }
    elif target_browser in ["chrome", "edge"]:
        if "browser_specific_settings" in manifest:
            del manifest["browser_specific_settings"]

    # Get script directory for absolute path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Create browser output directory if it doesn't exist
    browser_output_dir = os.path.join(script_dir, target_browser)
    os.makedirs(browser_output_dir, exist_ok=True)
    
    try:
        if target_browser == "firefox":
            # For Firefox, create a temporary folder, then zip it and rename to .xpi
            import tempfile
            import zipfile
            from datetime import datetime
            import time
            
            # Create a temp directory for building the extension
            with tempfile.TemporaryDirectory() as temp_dir:
                print(f"Creating temporary directory for Firefox extension: {temp_dir}")
                
                # Copy all files from extension folder to temp directory
                for item in os.listdir(extension_folder):
                    item_path = os.path.join(extension_folder, item)
                    if os.path.isdir(item_path):
                        dest_dir = os.path.join(temp_dir, item)
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir)  # Remove if exists to avoid merge conflicts
                        shutil.copytree(item_path, dest_dir)
                    else:
                        shutil.copy2(item_path, temp_dir)
                
                # Write updated manifest to temp directory
                with open(os.path.join(temp_dir, "manifest.json"), "w", encoding="utf-8") as file:
                    json.dump(manifest, file, indent=4)
                
                # Add a package.json file for web-ext tool compatibility
                package_json = {
                    "name": safe_name.lower().replace(" ", "-"),
                    "version": manifest.get("version", "1.0"),
                    "description": manifest.get("description", "Converted Chrome extension"),
                    "main": "manifest.json"
                }
                
                with open(os.path.join(temp_dir, "package.json"), "w", encoding="utf-8") as f:
                    json.dump(package_json, f, indent=4)
                
                # Create .xpi file (for distribution)
                safe_filename = safe_name.replace(" ", "_")
                xpi_path = os.path.join(browser_output_dir, f"{safe_filename}.xpi")
                
                # Also create a folder version for temporary installation
                temp_addon_dir = os.path.join(browser_output_dir, safe_name)
                if os.path.exists(temp_addon_dir):
                    shutil.rmtree(temp_addon_dir)
                shutil.copytree(temp_dir, temp_addon_dir)
                
                # Remove existing .xpi file if it exists
                if os.path.exists(xpi_path):
                    os.remove(xpi_path)
                
                # Use a current timestamp for all files in the zip
                now = time.localtime(time.time())[:6]
                
                # Create the zip file
                with zipfile.ZipFile(xpi_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    # Add all files from temp directory to the zip file
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Calculate the relative path for the zip file
                            rel_path = os.path.relpath(file_path, temp_dir)
                            
                            # Create a new ZipInfo with current timestamp
                            info = zipfile.ZipInfo(rel_path, now)
                            info.compress_type = zipfile.ZIP_DEFLATED
                            
                            # Read the content and add it to the zip with current date
                            with open(file_path, 'rb') as fd:
                                content = fd.read()
                                zipf.writestr(info, content)
                
                if os.path.exists(xpi_path):
                    print(f"Successfully converted '{ext_name}' to Firefox format.")
                    print(f"Saved as: {xpi_path}")
                    print(f"Unpackaged version (for temporary loading): {temp_addon_dir}")
                else:
                    print(f"Failed to create .xpi file for {ext_name}")
        else:
            # For Chrome and Edge, use the regular folder structure
            output_folder = os.path.join(browser_output_dir, safe_name)
            
            # Make sure output directory exists
            os.makedirs(output_folder, exist_ok=True)
            print(f"Creating output directory: {output_folder}")
            
            # Copy all files from extension folder
            for item in os.listdir(extension_folder):
                item_path = os.path.join(extension_folder, item)
                if os.path.isdir(item_path):
                    dest_dir = os.path.join(output_folder, item)
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)  # Remove if exists to avoid merge conflicts
                    shutil.copytree(item_path, dest_dir)
                else:
                    shutil.copy2(item_path, output_folder)

            # Write updated manifest
            with open(os.path.join(output_folder, "manifest.json"), "w", encoding="utf-8") as file:
                json.dump(manifest, file, indent=4)

            if os.path.exists(output_folder):
                print(f"Successfully converted '{ext_name}' to {target_browser} format.")
                print(f"Saved to: {output_folder}")
            else:
                print(f"Failed to create output folder for {ext_name}")
                
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

def test_extension_with_web_ext(extension_path):
    """Test the extension with web-ext if available."""
    try:
        import subprocess
        result = subprocess.run(["web-ext", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print("Testing extension with web-ext...")
            subprocess.run(["web-ext", "lint", "--source-dir", extension_path], capture_output=True, text=True)
            return True
    except FileNotFoundError:
        print("web-ext tool not found. For more thorough testing, install: npm install -g web-ext")
    return False

def main():
    # Set fixed browsers
    current_browser = "chrome"
    target_browser = "firefox"
    
    print("Extension Porter: Chrome → Firefox Converter")
    print("-------------------------------------------")
    
    profiles = get_browser_profiles(current_browser)

    if not profiles:
        print("No Chrome profiles found.")
        return

    print("Available Chrome profiles:")
    for idx, profile in enumerate(profiles, start=1):
        profile_name = os.path.basename(profile)
        print(f"{idx}. {profile_name}")

    profile_choice = input("Select a Chrome profile by number: ")
    if not profile_choice.isdigit() or not (1 <= int(profile_choice) <= len(profiles)):
        print("Invalid selection.")
        return

    selected_profile = profiles[int(profile_choice) - 1]
    extensions = get_extensions_from_profile(selected_profile, current_browser)

    if not extensions:
        print("No extensions found in the selected Chrome profile.")
        return

    print("\nInstalled Chrome extensions:")
    for idx, (ext_id, ext_name) in enumerate(extensions, start=1):
        print(f"{idx}. {ext_name}")

    print("\nOptions:")
    print("1-N: Select specific extensions by number")
    print("all: Process all extensions")
    
    selection = input("Enter numbers of extensions to convert (comma-separated) or 'all': ").strip().lower()
    
    if selection == "all":
        selected_extensions = [ext[0] for ext in extensions]  # Extract all extension IDs
    else:
        selected = selection.split(',')
        selected_extensions = [extensions[int(i)-1][0] for i in selected if i.isdigit() and 0 < int(i) <= len(extensions)]

    if not selected_extensions:
        print("No valid extensions selected.")
        return

    print(f"\nConverting {len(selected_extensions)} extensions from Chrome to Firefox...")
    for ext_id in selected_extensions:
        convert_extension(ext_id, selected_profile, target_browser, current_browser)

    print("\nConversion complete.")
    firefox_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firefox')
    print(f"Firefox extensions (.xpi files) have been saved to: {firefox_dir}")
    
    # Create README with instructions
    readme_path = os.path.join(firefox_dir, "README.txt")
    with open(readme_path, "w") as readme:
        readme.write("Firefox Extension Installation Instructions\n")
        readme.write("=====================================\n\n")
        readme.write("Due to Firefox's signing requirements, there are several ways to use these extensions:\n\n")
        readme.write("Option 1: Temporary Installation (Easiest, but only lasts until Firefox restarts)\n")
        readme.write("----------------------------------------------------------------\n")
        readme.write("1. Open Firefox and go to about:debugging\n")
        readme.write("2. Click 'This Firefox'\n")
        readme.write("3. Click 'Load Temporary Add-on...'\n")
        readme.write("4. Browse to the folder for each extension and select the manifest.json file\n\n")
        readme.write("Option 2: Use Firefox Developer Edition or Nightly\n")
        readme.write("----------------------------------------------------------------\n")
        readme.write("1. Download and install Firefox Developer Edition or Firefox Nightly\n")
        readme.write("2. Go to about:config and set xpinstall.signatures.required to false\n")
        readme.write("3. Then you can install the .xpi files directly\n\n")
        readme.write("Option 3: Use Firefox ESR\n")
        readme.write("----------------------------------------------------------------\n")
        readme.write("1. Download and install Firefox ESR\n")
        readme.write("2. Go to about:config and set xpinstall.signatures.required to false\n")
        readme.write("3. Then you can install the .xpi files directly\n")
        readme.write("\nOption 4: Submit to Mozilla for Official Signing\n")
        readme.write("----------------------------------------------------------------\n")
        readme.write("For permanent installation in regular Firefox:\n")
        readme.write("1. Create a developer account at https://addons.mozilla.org\n")
        readme.write("2. Use web-ext tool to package and submit your extension:\n")
        readme.write("   npm install -g web-ext\n")
        readme.write("   cd [extension_folder]\n")
        readme.write("   web-ext lint\n")
        readme.write("   web-ext build\n")
        readme.write("3. Upload the generated .zip file to https://addons.mozilla.org/developers/\n")
        readme.write("4. Wait for Mozilla review and approval\n")
    
    print("\nInstallation Instructions:")
    print("1. Open Firefox and go to about:debugging")
    print("2. Click 'This Firefox'")
    print("3. Click 'Load Temporary Add-on...'")
    print("4. Navigate to the extension folders and select manifest.json")
    print("\nSee the README.txt file in the firefox folder for more options.")

    print("\n⚠️ IMPORTANT NOTE: ⚠️")
    print("Extensions cannot be permanently installed in regular Firefox without being signed by Mozilla.")
    print("The temporary installation method works but extensions will need to be reinstalled after each restart.")
    print("For permanent use, consider using Firefox Developer Edition, Nightly, or ESR as described in the README.")

if __name__ == "__main__":
    main()