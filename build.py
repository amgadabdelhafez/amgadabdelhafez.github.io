import os
import shutil
import re
import subprocess
from xml.etree import ElementTree as ET

def delete_folder(folder_path):
    if os.path.exists(folder_path):
        shutil.rmtree(folder_path)
        print(f"Deleted folder: {folder_path}")

def delete_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)
        print(f"Deleted file: {file_path}")

def update_addon_xml(file_path):
    print(f"Checking addon.xml at: {file_path}")
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        print(f"Root tag: {root.tag}")
        print(f"Root attributes: {root.attrib}")
        
        if root.tag != 'addon':
            print("Error: Root element is not 'addon'.")
            return None
        
        current_version = root.get('version')
        if current_version is None:
            print("Error: 'version' attribute not found in the 'addon' element.")
            return None
        
        print(f"Current addon.xml version: {current_version}")
        return current_version
    except Exception as e:
        print(f"An error occurred while checking addon.xml: {str(e)}")
        return None

def update_index_html(file_path, new_version):
    with open(file_path, 'r') as file:
        content = file.read()
    
    updated_content = re.sub(r'plugin\.video\.skipintro-\d+\.\d+\.\d+\.zip', f'plugin.video.skipintro-{new_version}.zip', content)
    
    if updated_content != content:
        with open(file_path, 'w') as file:
            file.write(updated_content)
        print(f"Updated index.html version to: {new_version}")
    else:
        print("Warning: No changes were made to index.html. The version might already be up to date.")

def run_repo_generator():
    subprocess.run(['python', '_repo_generator.py'], check=True)
    print("Ran _repo_generator.py successfully")

def copy_new_zip_to_root(new_version):
    source_path = f'repo/zips/plugin.video.skipintro/plugin.video.skipintro-{new_version}.zip'
    destination_path = f'plugin.video.skipintro-{new_version}.zip'
    shutil.copy2(source_path, destination_path)
    print(f"Copied new addon zip to root: {destination_path}")

def main():
    # Delete 'zips' folder
    delete_folder('repo/zips')

    # Delete addon zip in root folder
    for file in os.listdir():
        if file.startswith('plugin.video.skipintro-') and file.endswith('.zip'):
            delete_file(file)

    # Check addon.xml and get current version
    current_version = update_addon_xml('repo/repository.skipintro/addon.xml')
    if current_version is None:
        print("Failed to read addon.xml. Build process aborted.")
        return

    # Update index.html
    update_index_html('index.html', current_version)

    # Run _repo_generator.py
    run_repo_generator()

    # Copy new zip file to root
    copy_new_zip_to_root(current_version)

if __name__ == "__main__":
    main()
    print("Build process completed successfully.")
