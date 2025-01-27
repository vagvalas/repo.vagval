import xbmc
import xbmcgui
import xbmcaddon
import xbmcplugin
import xbmcvfs
import urllib.request
import zipfile
import os
import urllib.parse
import ssl
import shutil
import time
import platform

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')
addon_handle = int(sys.argv[1])

# Define the list of builds with their URLs
builds = [
    {"name": "Main clean build for 21.x:", "url": None},  # Info line (dummy entry)
    {"name": "Build21.x", "url": "https://github.com/vagvalas/repo.vagval/releases/download/RELEASE/Build_21.x.zip"}
]

# Define the download path (use xbmcvfs.translatePath for Kodi 19+)
download_path = xbmcvfs.translatePath('special://home/')

def list_builds():
    # Create and add list items for each build
    for build in builds:
        list_item = xbmcgui.ListItem(label=build['name'])
        list_item.setInfo('video', {'title': build['name'], 'genre': 'Build'})
        
        if build["url"] is None:
            # Skip adding action or URL for this item (it will just appear as text)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url='', listitem=list_item, isFolder=False)
        else:
            # Create a URL for each build that will trigger the install function
            url = f'{sys.argv[0]}?action=install&url={build["url"]}&name={build["name"]}'
            
            # Add the list item to the directory
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=list_item, isFolder=False)

    # End of directory to tell Kodi the directory is ready
    xbmcplugin.endOfDirectory(addon_handle)

def delete_existing_folders():
    try:
        # Define the paths for the existing "addons" and "userdata" folders
        addons_path = xbmcvfs.translatePath('special://home/addons/')
        userdata_path = xbmcvfs.translatePath('special://home/userdata/')

        # Function to remove read-only attributes before deletion
        def force_remove_readonly(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)  # Remove read-only attribute
                func(path)
            except Exception as e:
                xbmcgui.Dialog().notification('Wizard', f'Failed to delete: {path}', xbmcgui.NOTIFICATION_WARNING)

        # Function to delete a folder safely
        def safe_delete(folder_path):
            try:
                if os.path.exists(folder_path):
                    shutil.rmtree(folder_path, onerror=force_remove_readonly)
                    xbmcgui.Dialog().notification('Wizard', f'Deleted: {folder_path}')
            except Exception as e:
                xbmcgui.Dialog().notification('Wizard', f'Error deleting {folder_path}: {str(e)}', xbmcgui.NOTIFICATION_ERROR)

        # Check if the OS is Windows
        if platform.system() == 'Windows':
            xbmcgui.Dialog().notification('Wizard', 'Attempting forced delete for Windows...')

            # Force remove read-only attributes and delete
            safe_delete(addons_path)
            safe_delete(userdata_path)
        else:
            # Standard deletion process for other OS (Linux/macOS)
            xbmcgui.Dialog().notification('Wizard', 'Deleting folders on non-Windows OS...')
            safe_delete(addons_path)
            safe_delete(userdata_path)

    except Exception as e:
        xbmcgui.Dialog().notification('Wizard', f'Error deleting folders: {str(e)}', xbmcgui.NOTIFICATION_ERROR)

ssl._create_default_https_context = ssl._create_unverified_context

def download_build(url, build_name):
    # Define the download path and file name
    zip_path = os.path.join(download_path, f"{build_name}.zip")
    
    try:
        # Create a progress dialog
        progress_dialog = xbmcgui.DialogProgress()
        progress_dialog.create(f"Downloading {build_name}", "Initializing download...")
        
        # Use Wget user-agent to simulate wget download behavior
        headers = {'User-Agent': 'Wget/1.16 (linux-gnu)'}
        request = urllib.request.Request(url, headers=headers)

        # Open the URL to get the file size (to show progress)
        with urllib.request.urlopen(request) as response:
            total_size = int(response.getheader('Content-Length').strip())
            downloaded_size = 0
            start_time = time.time()

            # Open the destination file
            with open(zip_path, 'wb') as out_file:
                while True:
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    out_file.write(chunk)

                    # Update the downloaded size
                    downloaded_size += len(chunk)

                    # Calculate progress percentage
                    percent = int((downloaded_size / total_size) * 100)

                    # Calculate download speed (bytes per second)
                    elapsed_time = time.time() - start_time
                    speed = downloaded_size / elapsed_time if elapsed_time > 0 else 0
                    speed_kb = speed / 1024  # Speed in KB/s

                    # Update the progress dialog
                    progress_dialog.update(percent, f"Downloaded {downloaded_size // 1024} KB of {total_size // 1024} KB")

                    # Allow user to cancel the download
                    if progress_dialog.iscanceled():
                        raise Exception("Download canceled by user.")

        # Close the progress dialog
        progress_dialog.close()

        xbmcgui.Dialog().notification('Build Wizard', f'Download complete for {build_name}!')
    except Exception as e:
        progress_dialog.close()
        xbmcgui.Dialog().notification('Build Wizard', f'Error: {str(e)}', xbmcgui.NOTIFICATION_ERROR)
        return None

    return zip_path

def delete_build_zip(build_name):
    try:
        # Define the path where the build was downloaded
        download_path = xbmcvfs.translatePath('special://home/')
        
        # Construct the expected filename of the downloaded zip (assuming format "build_name.zip")
        zip_file = os.path.join(download_path, f"{build_name}.zip")
        
        # Check if the zip file exists
        if os.path.exists(zip_file):
            # Delete the zip file
            os.remove(zip_file)
            xbmcgui.Dialog().notification('Build Wizard', f'{build_name}.zip has been deleted.')
        else:
            xbmcgui.Dialog().notification('Build Wizard', f'{build_name}.zip not found.', xbmcgui.NOTIFICATION_ERROR)
    
    except Exception as e:
        xbmcgui.Dialog().notification('Build Wizard', f'Error deleting zip: {str(e)}', xbmcgui.NOTIFICATION_ERROR)

def extract_zip(zip_path):
    try:
        download_path = xbmcvfs.translatePath('special://home/')
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            if platform.system() == 'Windows':
                xbmcgui.Dialog().notification('Wizard', 'Extracting files with error handling (Windows)...')

                # Attempt to extract each file individually and ignore errors
                for file in zip_ref.namelist():
                    try:
                        zip_ref.extract(file, download_path)
                    except Exception as e:
                        xbmcgui.Dialog().notification('Wizard', f'Ignoring error: {file}', xbmcgui.NOTIFICATION_WARNING)

            else:
                # Extract normally on non-Windows OS
                zip_ref.extractall(download_path)
        
        xbmcgui.Dialog().notification('Wizard', 'Build installed successfully!')

    except zipfile.BadZipFile:
        xbmcgui.Dialog().notification('Wizard', 'Error: Bad zip file.', xbmcgui.NOTIFICATION_ERROR)
    except Exception as e:
        xbmcgui.Dialog().notification('Wizard', f'Extraction failed: {str(e)}', xbmcgui.NOTIFICATION_ERROR)

def install_build(url, build_name):
    zip_path = download_build(url, build_name)
    delete_existing_folders()
    extract_zip(zip_path)
    delete_build_zip(build_name)
    xbmcgui.Dialog().ok('Build Wizard', f'Installation complete for {build_name}![CR]Quit Kodi')
    os._exit(1)  # Restart Kodi after installation


# Handle navigation and install actions
def router(paramstring):
    # Parse query string into a dictionary using urllib.parse.parse_qsl for more reliable parsing
    params = dict(urllib.parse.parse_qsl(paramstring))
    
    # If the action is to install, get the build URL and name
    if params.get('action') == 'install':
        install_build(params['url'], params['name'])
    else:
        list_builds()

if __name__ == '__main__':
    # Call the router function with the query string from Kodi
    router(sys.argv[2][1:])  # Pass in the query string (removing the "?" at the start)