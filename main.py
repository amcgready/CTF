import os
import json
import shutil
import platform
import urllib.request
import urllib.parse
import logging
import logging.handlers
import time
from datetime import datetime

# Set up logging with rotation
def setup_logging():
    """Setup logging with rotation to keep only one log file."""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Create a timestamp for the log file name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"extension_porter_{timestamp}.log")
    
    # Configure logging
    log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Limit to one log file with 5MB max size
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=0
    )
    
    file_handler.setFormatter(log_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Set to debug for more verbose logging if needed
    
    # Remove existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(file_handler)
    
    # Log startup information
    logging.info("=" * 50)
    logging.info(f"Extension Porter started on {platform.system()} {platform.release()}")
    logging.info(f"Python version: {platform.python_version()}")
    logging.info("=" * 50)
    
    return log_file

def print_yellow(message):
    """Print message in yellow."""
    print(f"\033[93m{message}\033[0m")
    logging.info(f"[WARN] {message}")

def print_green(message):
    """Print message in green."""
    print(f"\033[92m{message}\033[0m")
    logging.info(f"[SUCCESS] {message}")

def search_firefox_addon_alternative(ext_name):
    """Search Mozilla Add-ons for alternatives based on name."""
    import logging
    
    logging.info(f"Searching Firefox add-ons for: {ext_name}")
    
    try:
        search_query = urllib.parse.quote(ext_name)
        url = f"https://addons.mozilla.org/api/v4/addons/search/?q={search_query}&app=firefox&type=extension&sort=relevance"
        
        logging.info(f"API URL: {url}")
        
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read())
            
            if data.get('results') and len(data['results']) > 0:
                print(f"\n🔍 Potential Firefox alternatives for '{ext_name}':")
                logging.info(f"Found {len(data['results'])} potential Firefox alternatives")
                
                for idx, addon in enumerate(data['results'][:3], 1):  # Show top 3
                    # Get addon name and handle multilingual names
                    addon_name = addon['name'].get('en-US', '')
                    if not addon_name and len(addon['name']) > 0:
                        # Get first available name if en-US not available
                        addon_name = list(addon['name'].values())[0]
                        
                    # Get rating information
                    rating = addon.get('average_rating', 0)
                    users = addon.get('average_daily_users', 0)
                    
                    # Get addon ID
                    addon_id = addon.get('guid', 'unknown')
                    
                    # Format users count for better readability
                    if users >= 1000000:
                        users_display = f"{users/1000000:.1f}M users"
                    elif users >= 1000:
                        users_display = f"{users/1000:.1f}K users"
                    else:
                        users_display = f"{users} users"
                    
                    # Display addon with ID in parentheses
                    print(f"{idx}. {addon_name} ({addon_id})")
                    print(f"   Rating: {rating:.1f}/5 • {users_display}")
                    print(f"   https://addons.mozilla.org{addon['url']}")
                    
                    logging.info(f"Alternative {idx}: {addon_name} ({addon_id}), Rating: {rating:.1f}, Users: {users}")
                
                return True
            else:
                logging.info(f"No Firefox add-on alternatives found for: {ext_name}")
        
        return False
    except urllib.error.URLError as e:
        print_yellow(f"Network error searching for alternatives: {e}")
        logging.error(f"Network error searching for alternatives: {e}")
        return False
    except Exception as e:
        print_yellow(f"Error searching for alternatives: {e}")
        logging.error(f"Error searching for alternatives: {e}")
        return False

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

    try:
        with open(manifest_path, "r", encoding="utf-8") as file:
            try:
                manifest = json.load(file)
                ext_name = get_extension_name(manifest, extension_id, extension_folder)
            except json.JSONDecodeError:
                # Try with utf-8-sig encoding (handles BOM)
                file.seek(0)
                content = file.read()
                manifest = json.loads(content)
                ext_name = get_extension_name(manifest, extension_id, extension_folder)
    except Exception as e:
        print(f"Error reading manifest file: {e}")
        print_yellow(f"Skipping extension {extension_id}")
        return

    # Check for commercial extensions FIRST before attempting conversion
    commercial_extensions = [
        "efaidnbmnnnibpcajpcglclefindmkaj",  # Adobe Acrobat
        "aohghmighlieiainnegkcijnfilokake",  # Google Docs
        "ghbmnnjooekpmoecnnnilnnbdlolhkhi",  # Google Docs Offline
        # Add more known extension IDs
    ]
    
    if extension_id in commercial_extensions:
        print(f"\n🟥 Warning: {ext_name} is a commercial extension")
        print("🟥 Commercial extensions contain proprietary code that cannot be converted")
        
        # Try to find official alternative first
        if find_alternative_extension(extension_id, ext_name):
            return
            
        # If no direct mapping exists, search for alternatives online
        if search_firefox_addon_alternative(ext_name):
            choice = input("\nCreate placeholder instead? (y/n): ")
            if choice.lower() != 'y':
                return
        
        # Create placeholder as last resort
        convert_commercial_extension(extension_id, extension_folder, 
                                    target_browser, ext_name, 
                                    os.path.dirname(os.path.abspath(__file__)))
        return
    
    # Continue with regular conversion for non-commercial extensions
    print(f"\n🟦 Converting standard extension: {ext_name}")

    # Apply fixes to manifest before conversion
    manifest = fix_manifest_issues(manifest, target_browser)

    # Create safe folder name from extension name
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in ext_name).strip()
    
    if target_browser == "firefox":
        manifest["browser_specific_settings"] = {
            "gecko": {"id": f"{safe_name.lower().replace(' ', '_')}@firefox"}
        }
    elif target_browser in ["chrome", "edge"]:
        if "browser_specific_settings" in manifest:
            del manifest["browser_specific_settings"]

    # Fix manifest issues for target browser
    manifest = fix_manifest_issues(manifest, target_browser)

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
                # Add error handling for long paths or other copy errors
                skipped_files = []
                
                for item in os.listdir(extension_folder):
                    item_path = os.path.join(extension_folder, item)
                    try:
                        if os.path.isdir(item_path):
                            dest_dir = os.path.join(temp_dir, item)
                            if os.path.exists(dest_dir):
                                shutil.rmtree(dest_dir)  # Remove if exists to avoid merge conflicts
                                
                            # Use a safer copying method with error handling
                            try:
                                os.makedirs(dest_dir, exist_ok=True)
                                for root, dirs, files in os.walk(item_path):
                                    for file in files:
                                        src_file = os.path.join(root, file)
                                        # Create relative path
                                        rel_path = os.path.relpath(src_file, item_path)
                                        dst_file = os.path.join(dest_dir, rel_path)
                                        
                                        # Create directory structure if needed
                                        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                                        
                                        try:
                                            # Copy the file
                                            shutil.copy2(src_file, dst_file)
                                        except (OSError, shutil.Error) as e:
                                            print_yellow(f"Warning: Could not copy file {file}: {e}")
                                            skipped_files.append(f"{rel_path}")
                            except Exception as e:
                                print_yellow(f"Warning: Could not copy directory {item}: {e}")
                                skipped_files.append(item)
                        else:
                            try:
                                shutil.copy2(item_path, temp_dir)
                            except (OSError, shutil.Error) as e:
                                print_yellow(f"Warning: Could not copy file {item}: {e}")
                                skipped_files.append(item)
                    except Exception as e:
                        print_yellow(f"Warning: Error processing {item}: {e}")
                        skipped_files.append(item)
                
                if skipped_files:
                    print_yellow(f"Warning: Skipped {len(skipped_files)} files during copy operation.")
                
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
                    
                # Copy to final temporary installation folder with error handling
                try:
                    os.makedirs(temp_addon_dir, exist_ok=True)
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            src_file = os.path.join(root, file)
                            # Create relative path
                            rel_path = os.path.relpath(src_file, temp_dir)
                            dst_file = os.path.join(temp_addon_dir, rel_path)
                            
                            # Create directory structure if needed
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            
                            try:
                                # Copy the file
                                shutil.copy2(src_file, dst_file)
                            except (OSError, shutil.Error) as e:
                                print_yellow(f"Warning: Could not copy file to output folder: {e}")
                except Exception as e:
                    print_yellow(f"Warning: Error copying to output folder: {e}")
                
                # Create optimized XPI file
                xpi_created = create_firefox_xpi(temp_dir, xpi_path, manifest)
                
                if xpi_created and os.path.exists(xpi_path):
                    # Validate the XPI file before confirming success
                    if validate_converted_extension(xpi_path, ext_name):
                        print_green(f"Successfully converted '{ext_name}' to Firefox format.")
                        print(f"Saved as: {xpi_path}")
                        print(f"Unpackaged version (for temporary loading): {temp_addon_dir}")
                    else:
                        print_yellow(f"Warning: '{ext_name}' XPI file may be corrupted.")
                        print(f"Use the unpacked version instead: {temp_addon_dir}")
                else:
                    print_yellow(f"Failed to create .xpi file for {ext_name}")
                    print(f"Try using the unpacked version at: {temp_addon_dir}")
        else:
            # For Chrome and Edge, use the regular folder structure
            output_folder = os.path.join(browser_output_dir, safe_name)
            
            # Make sure output directory exists
            os.makedirs(output_folder, exist_ok=True)
            print(f"Creating output directory: {output_folder}")
            
            # Copy all files from extension folder with error handling
            skipped_files = []
            
            for item in os.listdir(extension_folder):
                item_path = os.path.join(extension_folder, item)
                try:
                    if os.path.isdir(item_path):
                        dest_dir = os.path.join(output_folder, item)
                        if os.path.exists(dest_dir):
                            shutil.rmtree(dest_dir)  # Remove if exists to avoid merge conflicts
                        
                        # Use a safer copying method with error handling
                        try:
                            os.makedirs(dest_dir, exist_ok=True)
                            for root, dirs, files in os.walk(item_path):
                                for file in files:
                                    src_file = os.path.join(root, file)
                                    # Create relative path
                                    rel_path = os.path.relpath(src_file, item_path)
                                    dst_file = os.path.join(dest_dir, rel_path)
                                    
                                    # Create directory structure if needed
                                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                                    
                                    try:
                                        # Copy the file
                                        shutil.copy2(src_file, dst_file)
                                    except (OSError, shutil.Error) as e:
                                        print_yellow(f"Warning: Could not copy file {file}: {e}")
                                        skipped_files.append(f"{rel_path}")
                        except Exception as e:
                            print_yellow(f"Warning: Could not copy directory {item}: {e}")
                            skipped_files.append(item)
                    else:
                        try:
                            shutil.copy2(item_path, output_folder)
                        except (OSError, shutil.Error) as e:
                            print_yellow(f"Warning: Could not copy file {item}: {e}")
                            skipped_files.append(item)
                except Exception as e:
                    print_yellow(f"Warning: Error processing {item}: {e}")
                    skipped_files.append(item)

            if skipped_files:
                print_yellow(f"Warning: Skipped {len(skipped_files)} files during copy operation.")

            # Write updated manifest
            with open(os.path.join(output_folder, "manifest.json"), "w", encoding="utf-8") as file:
                json.dump(manifest, file, indent=4)

            if os.path.exists(output_folder):
                print_green(f"Successfully converted '{ext_name}' to {target_browser} format.")
                print(f"Saved to: {output_folder}")
            else:
                print(f"Failed to create output folder for {ext_name}")
                
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()

def create_firefox_xpi(extension_folder, output_path, manifest):
    """Create a Firefox-compatible XPI file with improved error handling."""
    import zipfile
    import time
    import os
    import threading
    import logging
    
    # Use a current timestamp for all files in the zip
    now = time.localtime(time.time())[:6]
    
    # Log this operation
    logging.info(f"Creating Firefox XPI: {os.path.basename(output_path)}")
    
    # Extract extension name and ID for search and display
    extension_name = manifest.get("name", os.path.basename(extension_folder))
    extension_id = "unknown"
    
    # Extract ID from manifest if possible
    if "browser_specific_settings" in manifest and "gecko" in manifest["browser_specific_settings"]:
        extension_id = manifest["browser_specific_settings"]["gecko"].get("id", "unknown")
    
    # If name is a localization reference, try to get actual name
    if isinstance(extension_name, dict) or (isinstance(extension_name, str) and "__MSG_" in extension_name):
        # Get fallback name
        if isinstance(extension_name, str):
            msg_key = extension_name.replace("__MSG_", "").replace("__", "")
            logging.info(f"Extension name is localized: {msg_key} ({extension_id})")
        
        # Try short_name as fallback
        if "short_name" in manifest:
            extension_name = manifest["short_name"]
        else:
            extension_name = "extension"  # Default fallback
    
    logging.info(f"Processing extension: {extension_name} ({extension_id})")
    
    # Remove existing file if it exists
    if os.path.exists(output_path):
        try:
            os.remove(output_path)
        except PermissionError:
            print_yellow(f"Warning: Cannot overwrite existing XPI file (in use): {output_path}")
            logging.warning(f"Permission denied when removing existing XPI: {output_path}")
            # Try with alternate name
            base, ext = os.path.splitext(output_path)
            output_path = f"{base}_new{ext}"
            print_yellow(f"Trying alternate path: {output_path}")
            logging.info(f"Using alternate path: {output_path}")
        except Exception as e:
            print_yellow(f"Warning: Failed to remove existing XPI file: {e}")
            logging.warning(f"Error removing existing XPI: {e}")
            # Try with alternate name
            base, ext = os.path.splitext(output_path)
            output_path = f"{base}_new{ext}"
            print_yellow(f"Trying alternate path: {output_path}")
            logging.info(f"Using alternate path: {output_path}")
    
    # Start a background search for Firefox alternatives
    # Launch background search thread
    search_thread = threading.Thread(
        target=lambda: search_firefox_addon_alternative(extension_name),
        daemon=True
    )
    search_thread.start()
    logging.info(f"Started background search for Firefox alternative: {extension_name}")
    
    try:
        # Create a list to track problematic files
        skipped_files = []
        
        # Ensure manifest.json is written first in the XPI
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add manifest.json first (important for Firefox)
            manifest_path = os.path.join(extension_folder, "manifest.json")
            
            # Create manifest info
            info = zipfile.ZipInfo("manifest.json", now)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16  # Proper Unix file permissions
            
            # Write manifest content
            zipf.writestr(info, json.dumps(manifest, indent=2))
            
            # Add remaining files
            for root, dirs, files in os.walk(extension_folder):
                # Skip problematic directories that could cause issues
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__MACOSX' and 
                          d != '_metadata' and not d.endswith('.crx.directory')]
                
                for file in files:
                    # Skip manifest (already added) and problematic files
                    if (file == "manifest.json" or file.startswith('.') or 
                        file.startswith('~') or file == 'Thumbs.db' or
                        file.endswith('.crx') or file.endswith('.sig')):
                        continue
                    
                    try:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, extension_folder)
                        
                        # Skip very large files (likely binary components)
                        if os.path.getsize(file_path) > 10 * 1024 * 1024:  # 10MB limit
                            skipped_files.append(f"{rel_path} (too large)")
                            logging.warning(f"Skipped large file: {rel_path}")
                            continue
                            
                        # Skip problematic file paths
                        if len(rel_path) > 250:  # Avoid path length issues
                            skipped_files.append(f"{rel_path[:30]}...{rel_path[-30:]} (path too long)")
                            logging.warning(f"Skipped file with path too long: {rel_path[:30]}...")
                            continue
                            
                        # Check for non-text binary files that cause issues in Firefox
                        if any(rel_path.endswith(ext) for ext in ['.dll', '.so', '.dylib', '.exe', '.node']):
                            skipped_files.append(f"{rel_path} (native binary)")
                            logging.warning(f"Skipped native binary file: {rel_path}")
                            continue
                        
                        # Handle Windows-specific resource files that cause issues
                        if '\\resources\\app\\' in rel_path and rel_path.endswith('.asar'):
                            skipped_files.append(f"{rel_path} (Electron app resource)")
                            logging.warning(f"Skipped Electron resource file: {rel_path}")
                            continue
                            
                        # Set standard file info with permissions
                        info = zipfile.ZipInfo(rel_path, now)
                        info.compress_type = zipfile.ZIP_DEFLATED
                        info.external_attr = 0o100644 << 16  # Standard file permissions
                        
                        try:
                            # Add file content
                            with open(file_path, 'rb') as fd:
                                zipf.writestr(info, fd.read())
                        except (PermissionError, FileNotFoundError) as e:
                            skipped_files.append(f"{rel_path} (access error: {str(e)})")
                            print_yellow(f"Warning: Access error on file {rel_path}: {e}")
                            logging.warning(f"Access error on file {rel_path}: {e}")
                    except Exception as e:
                        skipped_files.append(f"{rel_path} ({str(e)})")
                        print_yellow(f"Warning: Skipping file {rel_path} due to: {e}")
                        logging.warning(f"Error processing file {rel_path}: {e}")
        
        # Report skipped files
        if skipped_files:
            print_yellow(f"Skipped {len(skipped_files)} problematic files during XPI creation:")
            logging.warning(f"Skipped {len(skipped_files)} problematic files during XPI creation")
            for file in skipped_files[:5]:  # Show first 5
                print_yellow(f"  - {file}")
                logging.warning(f"  - {file}")
            if len(skipped_files) > 5:
                print_yellow(f"  - ...and {len(skipped_files) - 5} more")
                logging.warning(f"  - ...and {len(skipped_files) - 5} more files")
            
            # Check if we skipped too many files (might indicate issues)
            total_files = sum(len(files) for _, _, files in os.walk(extension_folder))
            if total_files > 0 and len(skipped_files) / total_files > 0.5:
                print_yellow("Warning: More than 50% of files were skipped. The XPI may not work correctly.")
                logging.warning("More than 50% of files were skipped. The XPI may not work correctly.")
        
        # Verify the XPI file was created and is not empty
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            # Try to verify the ZIP integrity
            try:
                with zipfile.ZipFile(output_path, 'r') as check_zip:
                    # Just test the integrity, no extraction
                    bad_file = check_zip.testzip()
                    if bad_file is not None:
                        print_yellow(f"Warning: The created XPI file may be corrupted (bad file: {bad_file}).")
                        logging.warning(f"XPI integrity check failed: bad file {bad_file}")
                    else:
                        file_size_kb = os.path.getsize(output_path)/1024
                        print_green(f"XPI file created successfully: {os.path.basename(output_path)} ({file_size_kb:.1f} KB)")
                        logging.info(f"XPI file created successfully: {os.path.basename(output_path)} ({file_size_kb:.1f} KB)")
                        
                        # Add Firefox ID for easy reference
                        if "browser_specific_settings" in manifest and "gecko" in manifest["browser_specific_settings"]:
                            firefox_id = manifest["browser_specific_settings"]["gecko"].get("id", "unknown")
                            print(f"Firefox extension ID: {firefox_id}")
                            logging.info(f"Firefox extension ID: {firefox_id}")
            except Exception as e:
                print_yellow(f"Warning: Could not verify XPI file integrity: {e}")
                logging.warning(f"Could not verify XPI file integrity: {e}")
            
            # Wait for search thread to complete if it's still running (max 3 seconds)
            if search_thread.is_alive():
                logging.info(f"Waiting for Firefox alternative search to complete")
                search_thread.join(timeout=3)
                
            return True
        else:
            print_yellow(f"Error: Failed to create valid XPI file at {output_path}")
            logging.error(f"Failed to create valid XPI file at {output_path}")
            return False
    except Exception as e:
        print(f"Error creating XPI file: {e}")
        logging.error(f"Error creating XPI file: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        
        # Still show alternatives even if XPI creation failed
        if search_thread.is_alive():
            logging.info(f"Waiting for Firefox alternative search to complete after error")
            search_thread.join(timeout=3)
            
        return False

def get_browser_profiles(browser):
    """Get browser profiles based on operating system and browser type."""
    profiles = []
    system = platform.system()
    
    if system == "Windows":
        if browser == "chrome":
            # Chrome profiles on Windows
            user_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 
                                      'Google', 'Chrome', 'User Data')
            if os.path.exists(user_data_dir):
                for item in os.listdir(user_data_dir):
                    if (item.startswith('Profile ') or item == 'Default') and \
                       os.path.isdir(os.path.join(user_data_dir, item)):
                        profiles.append(os.path.join(user_data_dir, item))
        elif browser == "firefox":
            # Firefox profiles on Windows
            mozilla_dir = os.path.join(os.environ.get('APPDATA', ''), 'Mozilla', 'Firefox', 'Profiles')
            if os.path.exists(mozilla_dir):
                for item in os.listdir(mozilla_dir):
                    if os.path.isdir(os.path.join(mozilla_dir, item)):
                        profiles.append(os.path.join(mozilla_dir, item))
    elif system == "Darwin":  # macOS
        if browser == "chrome":
            # Chrome profiles on macOS
            user_data_dir = os.path.expanduser('~/Library/Application Support/Google/Chrome')
            if os.path.exists(user_data_dir):
                for item in os.listdir(user_data_dir):
                    if (item.startswith('Profile ') or item == 'Default') and \
                       os.path.isdir(os.path.join(user_data_dir, item)):
                        profiles.append(os.path.join(user_data_dir, item))
        elif browser == "firefox":
            # Firefox profiles on macOS
            mozilla_dir = os.path.expanduser('~/Library/Application Support/Firefox/Profiles')
            if os.path.exists(mozilla_dir):
                for item in os.listdir(mozilla_dir):
                    if os.path.isdir(os.path.join(mozilla_dir, item)):
                        profiles.append(os.path.join(mozilla_dir, item))
    elif system == "Linux":
        if browser == "chrome":
            # Chrome profiles on Linux
            user_data_dir = os.path.expanduser('~/.config/google-chrome')
            if os.path.exists(user_data_dir):
                for item in os.listdir(user_data_dir):
                    if (item.startswith('Profile ') or item == 'Default') and \
                       os.path.isdir(os.path.join(user_data_dir, item)):
                        profiles.append(os.path.join(user_data_dir, item))
        elif browser == "firefox":
            # Firefox profiles on Linux
            mozilla_dir = os.path.expanduser('~/.mozilla/firefox')
            if os.path.exists(mozilla_dir):
                for item in os.listdir(mozilla_dir):
                    if os.path.isdir(os.path.join(mozilla_dir, item)):
                        profiles.append(os.path.join(mozilla_dir, item))
    
    return profiles

def get_extensions_from_profile(profile_path, browser):
    """Get installed extensions from a browser profile."""
    extensions = []
    
    if browser == "chrome":
        # Chrome extensions are stored in the Extensions folder
        extensions_dir = os.path.join(profile_path, "Extensions")
        if os.path.exists(extensions_dir):
            for ext_id in os.listdir(extensions_dir):
                if not os.path.isdir(os.path.join(extensions_dir, ext_id)):
                    continue
                
                # Find the latest version folder
                ext_path = os.path.join(extensions_dir, ext_id)
                versions = [v for v in os.listdir(ext_path) if os.path.isdir(os.path.join(ext_path, v))]
                
                if not versions:
                    continue
                    
                latest_version = sorted(versions)[-1]
                manifest_path = os.path.join(ext_path, latest_version, "manifest.json")
                
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, "r", encoding="utf-8") as f:
                            try:
                                manifest = json.load(f)
                                ext_name = get_extension_name(manifest, ext_id, os.path.join(ext_path, latest_version))
                                extensions.append((ext_id, ext_name))
                            except json.JSONDecodeError:
                                # Try with utf-8-sig encoding
                                f.seek(0)
                                content = f.read()
                                manifest = json.loads(content)
                                ext_name = get_extension_name(manifest, ext_id, os.path.join(ext_path, latest_version))
                                extensions.append((ext_id, ext_name))
                    except Exception as e:
                        print_yellow(f"Warning: Could not read manifest for {ext_id}: {e}")
                        extensions.append((ext_id, f"Unknown Extension ({ext_id})"))
    
    return extensions

def get_extension_name(manifest, extension_id, extension_folder):
    """Get extension name from manifest, with fallbacks."""
    # Try to get name from manifest
    if manifest and "name" in manifest:
        name = manifest["name"]
        
        # Handle localized names
        if isinstance(name, dict) and "__MSG_" in str(name):
            # Check for default locale
            if "default_locale" in manifest:
                locale = manifest["default_locale"]
                messages_path = os.path.join(extension_folder, "_locales", locale, "messages.json")
                
                if os.path.exists(messages_path):
                    try:
                        with open(messages_path, "r", encoding="utf-8") as f:
                            messages = json.load(f)
                            
                            # Extract message name from format like "__MSG_extName__"
                            msg_key = name.replace("__MSG_", "").replace("__", "")
                            
                            if msg_key in messages and "message" in messages[msg_key]:
                                # Return name with ID in parentheses
                                return f"{messages[msg_key]['message']} ({extension_id})"
                    except:
                        pass
            
            # Try English as fallback
            messages_path = os.path.join(extension_folder, "_locales", "en", "messages.json")
            if os.path.exists(messages_path):
                try:
                    with open(messages_path, "r", encoding="utf-8") as f:
                        messages = json.load(f)
                        
                        # Extract message name from format like "__MSG_extName__"
                        msg_key = name.replace("__MSG_", "").replace("__", "")
                        
                        if msg_key in messages and "message" in messages[msg_key]:
                            # Return name with ID in parentheses
                            return f"{messages[msg_key]['message']} ({extension_id})"
                except:
                    pass
                    
            # If we still have a localized name, show the message key with ID
            return f"__MSG_{msg_key}__ ({extension_id})"
        else:
            # Direct string name with ID
            return f"{str(name)} ({extension_id})"
    
    # Fallback to short name
    if manifest and "short_name" in manifest:
        return f"{str(manifest['short_name'])} ({extension_id})"
    
    # Last resort: just use extension ID
    return f"Extension ({extension_id})"

def fix_manifest_issues(manifest, target_browser):
    """Fix common issues with manifest files when converting between browsers."""
    manifest_copy = manifest.copy()
    
    # Remove keys that are not compatible with Firefox
    if target_browser == "firefox":
        # Firefox doesn't support these Chrome-specific manifest keys
        keys_to_remove = [
            "key", "oauth2", "storage", "system_indicator", "update_url", 
            "externally_connectable.matches", "externally_connectable.accepts_tls_channel_id",
            "nacl_modules", "platforms", "requirements", "tts_engine"
        ]
        
        for key in keys_to_remove:
            if "." in key:
                parent, child = key.split(".", 1)
                if parent in manifest_copy and isinstance(manifest_copy[parent], dict) and child in manifest_copy[parent]:
                    del manifest_copy[parent][child]
            elif key in manifest_copy:
                del manifest_copy[key]
        
        # Convert manifest version if needed
        if "manifest_version" in manifest_copy and manifest_copy["manifest_version"] > 2:
            manifest_copy["manifest_version"] = 2  # Firefox uses manifest v2
            
        # Fix content security policy
        if "content_security_policy" in manifest_copy:
            if isinstance(manifest_copy["content_security_policy"], dict):
                # Convert to string format for Firefox
                if "extension_pages" in manifest_copy["content_security_policy"]:
                    manifest_copy["content_security_policy"] = manifest_copy["content_security_policy"]["extension_pages"]
    
    # Special fixes for Chrome/Edge
    elif target_browser in ["chrome", "edge"]:
        # Remove Firefox-specific keys
        if "applications" in manifest_copy:
            del manifest_copy["applications"]
        if "browser_specific_settings" in manifest_copy:
            del manifest_copy["browser_specific_settings"]
            
        # Ensure manifest version is appropriate
        if "manifest_version" in manifest_copy and manifest_copy["manifest_version"] < 3:
            # For production extensions, you might want to convert to v3
            # but it requires significant code changes, so keeping v2 for simplicity
            pass
    
    return manifest_copy

def validate_converted_extension(xpi_path, ext_name):
    """Validate that the converted XPI file is properly structured."""
    import zipfile
    
    if not os.path.exists(xpi_path):
        return False
    
    try:
        # Check file size - should be reasonable
        file_size = os.path.getsize(xpi_path)
        if file_size < 100:  # Too small to be valid
            print_yellow(f"Warning: XPI file for '{ext_name}' is suspiciously small ({file_size} bytes)")
            return False
            
        # Check ZIP integrity and manifest presence
        with zipfile.ZipFile(xpi_path, 'r') as zipf:
            # Check for manifest.json
            if "manifest.json" not in zipf.namelist():
                print_yellow(f"Warning: Missing manifest.json in XPI for '{ext_name}'")
                return False
                
            # Basic manifest parsing check
            try:
                manifest_data = zipf.read("manifest.json").decode('utf-8')
                json.loads(manifest_data)  # Just to verify it's valid JSON
            except:
                print_yellow(f"Warning: Invalid manifest.json in XPI for '{ext_name}'")
                return False
        
        return True
    except Exception as e:
        print_yellow(f"Warning: Error validating XPI for '{ext_name}': {e}")
        return False

def find_alternative_extension(extension_id, ext_name):
    """Find official alternative for known extensions."""
    # Define mapping of Chrome extension IDs to Firefox URLs
    firefox_alternatives = {
        "cjpalhdlnbpafiamejdnhcphjbkeiagm": {  # uBlock Origin
            "name": "uBlock Origin",
            "url": "https://addons.mozilla.org/firefox/addon/ublock-origin/"
        },
        "gcbommkclmclpchllfjekcdonpmejbdp": {  # HTTPS Everywhere
            "name": "HTTPS Everywhere",
            "url": "https://addons.mozilla.org/firefox/addon/https-everywhere/"
        },
        "dbepggeogbaibhgnhhndojpepiihcmeb": {  # Vimium
            "name": "Vimium",
            "url": "https://addons.mozilla.org/firefox/addon/vimium-ff/"
        },
        # Add more known mappings here
    }
    
    if extension_id in firefox_alternatives:
        alt = firefox_alternatives[extension_id]
        print_green(f"\nOfficial Firefox alternative found for {ext_name}:")
        print(f"Name: {alt['name']}")
        print(f"URL: {alt['url']}")
        return True
        
    return False

def convert_commercial_extension(extension_id, extension_folder, target_browser, ext_name, script_dir):
    """Create a placeholder extension for commercial extensions."""
    # Create a simple redirect extension
    browser_output_dir = os.path.join(script_dir, target_browser)
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in ext_name).strip()
    
    output_folder = os.path.join(browser_output_dir, f"{safe_name} (Placeholder)")
    os.makedirs(output_folder, exist_ok=True)
    
    # Create minimal manifest
    basic_manifest = {
        "manifest_version": 2,
        "name": f"{ext_name} (Placeholder)",
        "version": "1.0",
        "description": f"Placeholder for {ext_name} - redirects to official download page",
        "icons": {
            "48": "icon.png",
            "96": "icon.png"
        },
        "browser_action": {
            "default_icon": "icon.png",
            "default_popup": "popup.html"
        },
        "permissions": []
    }
    
    # Add browser specific settings for Firefox
    if target_browser == "firefox":
        basic_manifest["browser_specific_settings"] = {
            "gecko": {
                "id": f"{safe_name.lower().replace(' ', '_')}.placeholder@firefox"
            }
        }
    
    # Write manifest
    with open(os.path.join(output_folder, "manifest.json"), "w") as f:
        json.dump(basic_manifest, f, indent=2)
    
    # Create a simple icon (blank 96x96 PNG with border)
    try:
        from PIL import Image, ImageDraw
        img = Image.new('RGBA', (96, 96), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (95, 95)], outline="gray", width=2)
        img.save(os.path.join(output_folder, "icon.png"))
    except ImportError:
        # If PIL is not installed, download a simple icon
        try:
            url = "https://raw.githubusercontent.com/mozilla/addons-server/master/static/img/addon-icons/default-64.png"
            urllib.request.urlretrieve(url, os.path.join(output_folder, "icon.png"))
        except:
            # If download fails, create an empty file
            with open(os.path.join(output_folder, "icon.png"), "wb") as f:
                pass
    
    # Create popup HTML with link to Firefox alternatives
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; width: 300px; }}
            h2 {{ color: #333; }}
            .warning {{ color: #cc0000; }}
            .button {{ background-color: #0060df; color: white; padding: 10px 15px; 
                      border: none; border-radius: 4px; cursor: pointer; display: inline-block;
                      text-decoration: none; margin-top: 10px; }}
            .button:hover {{ background-color: #003eaa; }}
        </style>
    </head>
    <body>
        <h2>{ext_name} (Placeholder)</h2>
        <p class="warning">This is a placeholder extension.</p>
        <p>The original extension contains proprietary code and cannot be converted automatically.</p>
        <p>Please visit the Firefox Add-ons store to search for an alternative:</p>
        <a class="button" href="https://addons.mozilla.org/firefox/search/?q={urllib.parse.quote(ext_name)}" target="_blank">
            Search for Alternatives
        </a>
    </body>
    </html>
    """
    
    with open(os.path.join(output_folder, "popup.html"), "w") as f:
        f.write(html_content)
    
    print_green(f"Created placeholder extension for '{ext_name}'")
    print(f"Placeholder saved to: {output_folder}")
    
    # For Firefox, also create an XPI
    if target_browser == "firefox":
        import zipfile
        import time
        
        safe_filename = safe_name.replace(" ", "_")
        xpi_path = os.path.join(browser_output_dir, f"{safe_filename}_placeholder.xpi")
        
        # Create XPI file
        with zipfile.ZipFile(xpi_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Use current timestamp
            now = time.localtime(time.time())[:6]
            
            # Add manifest first
            info = zipfile.ZipInfo("manifest.json", now)
            info.external_attr = 0o644 << 16
            with open(os.path.join(output_folder, "manifest.json"), 'rb') as f:
                zipf.writestr(info, f.read())
            
            # Add other files
            for filename in ["icon.png", "popup.html"]:
                info = zipfile.ZipInfo(filename, now)
                info.external_attr = 0o644 << 16
                with open(os.path.join(output_folder, filename), 'rb') as f:
                    zipf.writestr(info, f.read())
        
        print(f"Placeholder XPI saved to: {xpi_path}")
def main():
    # Set up logging
    log_file = setup_logging()
    
    # Set fixed browsers
    current_browser = "chrome"
    target_browser = "firefox"
    
    print("Extension Porter: Chrome → Firefox Converter")
    print("-------------------------------------------")
    # Fix: Replace Unicode arrow with ASCII alternative for logging
    logging.info("Starting Extension Porter: Chrome to Firefox Converter")
    print(f"Log file: {log_file}")
    
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