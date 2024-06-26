from icon import images
import customtkinter as ctk
from tkinter import messagebox
import tkinter.filedialog as fd
import tempfile
import os
import json
import glob
import argparse
import subprocess
import sys
import re
from zstd import Zstd

def get_correct_path(relative_path):
    try:
        # When running as a standalone executable
        base_path = sys._MEIPASS
    except Exception:
        # When running as a script
        if getattr(sys, 'frozen', False):
            # If the application is frozen using PyInstaller
            base_path = os.path.dirname(sys.executable)
        else:
            # If the application is run as a normal Python script
            base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# Get the absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = "dist"
dist_path = get_correct_path(dist_path)
if os.name == 'nt':  # Windows
    byml_to_yaml = os.path.join(dist_path, "byml-to-yaml.exe")
    tag_product = os.path.join(dist_path, "TagProductTool.exe")
else:  # Linux and macOS
    byml_to_yaml = os.path.join(dist_path, "byml-to-yaml")
    tag_product = os.path.join(dist_path, "TagProductTool")

master_dir = "master"
master_dir = get_correct_path(master_dir)

def count_common_lines(file_content, master_content):
    # Split the file content into lines
    file_lines = file_content.splitlines()
    master_lines = master_content.splitlines()
    # Count the number of identical lines
    identical_line_count = sum(f == m for f, m in zip(file_lines, master_lines))
    return identical_line_count

def find_most_similar_master_json(compared_file):
    master_dir = "master"
    master_dir = get_correct_path(master_dir)
    master_files = os.listdir(master_dir)
    master_files = [file for file in master_files if file.endswith(('.json'))]
    
    with open(compared_file, 'r') as file1:
        file1_content = file1.read()

    best_match_count = 0
    most_similar_master = None

    for master_file in master_files:
        master_path = os.path.join(master_dir, master_file)
        with open(master_path, 'r') as master:
            master_content = master.read()
            common_line_count = count_common_lines(file1_content, master_content)
            if common_line_count > best_match_count:
                best_match_count = common_line_count
                most_similar_master = master_file

    if most_similar_master:
        return most_similar_master
    else:
        print('No master found!')
        return None

def count_common_blocks(file_content, master_content):
    # Split the file content into blocks and strip any leading or trailing whitespaces
    file_blocks = set(block.strip() for block in file_content.split('\n-') if block)
    master_blocks = set(block.strip() for block in master_content.split('\n-') if block)
    # Count the number of identical blocks
    identical_block_count = len(file_blocks & master_blocks)
    return identical_block_count

def find_most_similar_master(compared_file):
    master_dir = "master"
    master_dir = get_correct_path(master_dir)
    master_files = os.listdir(master_dir)

    # Extract the prefix from the compared_file
    compared_file_parts = os.path.basename(compared_file).split('.')
    compared_file_prefix = '.'.join(compared_file_parts[:2])

    # Filter the master_files based on the prefix
    master_files = [file for file in master_files if file.startswith(compared_file_prefix) and file.endswith('.yaml')]
    
    with open(compared_file, 'r', encoding='utf-8') as file1:
        file1_content = file1.read()

    best_match_count = 0
    most_similar_master = None

    for master_file in master_files:
        master_path = os.path.join(master_dir, master_file)
        with open(master_path, 'r', encoding='utf-8') as master:
            master_content = master.read()
            common_block_count = count_common_blocks(file1_content, master_content)
            if common_block_count > best_match_count:
                best_match_count = common_block_count
                most_similar_master = master_file

    if most_similar_master:
        return most_similar_master
    else:
        print('No master found!')
        return None

def generate_changelog_for_json(json_data, master_data):
    changelog = {
        "Added blocks": [],
        "Edited blocks": []
    }

    # Process each actor in json_data
    for actor, tags in json_data["ActorTagData"].items():
        if actor in master_data["ActorTagData"]:
            # Compare the tags, not just the actor
            if tags != master_data["ActorTagData"][actor]:
                # Actor is edited
                changelog["Edited blocks"].append({actor: tags})
        else:
            # Actor is added
            changelog["Added blocks"].append({actor: tags})

    return changelog

def generate_changelog_for_yaml(file_path, master_file_path):
    # Load the file and master data
    with open(file_path, 'r', encoding='utf-8') as file:
        file_data = file.read().strip().split('\n-')
    with open(master_file_path, 'r', encoding='utf-8') as master_file:
        master_data = master_file.read().strip().split('\n-')

    changelog = {
        "Added blocks": [],
        "Edited blocks": []
    }

    # Determine the identifier based on the file name
    file_name = os.path.basename(file_path)
    if file_name.startswith("TagDef"):
        identifier = 'DisplayName'
    elif file_name.startswith("GameSafetySetting"):
        identifier = 'NameHash'
    elif file_name.startswith("RumbleCall"):
        identifier = ',Name'
    elif file_name.startswith("UIScreen"):
        identifier = ' Name'
    else:
        identifier = '__RowId'

    # Create a dictionary that maps each value to its corresponding master_block
    master_blocks = {}
    for block in master_data:
        if identifier == '__RowId':
            # Special handling for __RowId where the identifier is at the end of the block
            match = re.search(rf'{identifier}: (\S+)', block)
        else:
            match = re.search(rf'{identifier}: (.*?)(,|}}|\n)', block)
        if match:
            value = match.group(1).strip()
            master_blocks[value] = block

    # Process each block in file_data
    for block in file_data:
        if identifier == '__RowId':
            # Special handling for __RowId where the identifier is at the end of the block
            match = re.search(rf'{identifier}: (\S+)', block)
        else:
            match = re.search(rf'{identifier}: (.*?)(,|}}|\n)', block)
        if match:
            value = match.group(1).strip()
            master_block = master_blocks.get(value)
            if master_block is None:
                # Block is added
                if not block.startswith('-'):
                    block = '-' + block
                if not block.endswith('\n'):
                    block += "\n"
                changelog["Added blocks"].append(block)
            else:
                # Convert the lines in the blocks to sets and compare the sets
                file_block_set = set(block.split('\n'))
                master_block_set = set(master_block.split('\n'))
                if file_block_set != master_block_set:
                    # Block is edited
                    if not block.startswith('-'):
                        block = '-' + block
                    if not block.endswith('\n'):
                        block += "\n"
                    changelog["Edited blocks"].append(block)

    return changelog

def generate_changelogs(folder_path, output_path):
    # List of recognized types
    recognized_types = [
        "ActorInfo.Product", "AttachmentActorInfo.Product", "Challenge.Product", "EnhancementMaterialInfo.Product",
        "EventPlayEnvSetting.Product", "EventSetting.Product", "GameActorInfo.Product", "GameAnalyzedEventInfo.Product",
        "GameEventBaseSetting.Product", "GameEventMetadata.Product", "GameSafetySetting.Product", "LoadingTips.Product",
        "Location.Product", "LocatorData.Product", "PouchActorInfo.Product", "RumbleCall.Product", "Tag.Product", 
        "TagDef.Product", "UIScreen.Product", "XLinkPropertyTable.Product", "XLinkPropertyTableList.Product"
    ]

    # Initialize changelog dictionary with sections for each type
    changelog = {type_name: {"Added blocks": [], "Edited blocks": []} for type_name in recognized_types}

    # Dictionary to hold the latest version file for each type
    latest_files = {}

    # Identify the latest version file for each type
    for file_name in os.listdir(folder_path):
        for type_name in recognized_types:
            if file_name.startswith(type_name) and file_name.endswith('.rstbl.byml.zs'):
                version = int(file_name.split('.')[2])  # Assuming version is always an integer
                if type_name not in latest_files or version > latest_files[type_name][1]:
                    latest_files[type_name] = (file_name, version)

    # Decompress and convert .byml.zs files
    for type_name, (file_name, version) in latest_files.items():
        file_path = os.path.join(folder_path, file_name)
        if type_name == "Tag.Product":
            # Use TagProductTool.exe for "Tag.Product" type
            json_file_path = file_path + '.json'
            process = subprocess.run([tag_product, os.path.join(folder_path, file_name), folder_path], capture_output=True, text=True)
            if "INFO: Conversion Complete." in process.stdout:
                # Load the JSON data into a dictionary
                with open(json_file_path, 'r') as file:
                    json_data = json.load(file)
                
                # Find the most similar master file
                most_similar_master = find_most_similar_master_json(json_file_path)
                master_file_path = os.path.join(get_correct_path("master"), most_similar_master)
                print("Version detected:", most_similar_master[:-5])
                
                # Load the master JSON data into a dictionary
                with open(master_file_path, 'r') as file:
                    master_data = json.load(file)
                
                file_changelog = generate_changelog_for_json(json_data, master_data)  # You need to implement this function
                
                # Update the main changelog dictionary with the changes for this type
                changelog[type_name]["Added blocks"].extend(file_changelog["Added blocks"])
                changelog[type_name]["Edited blocks"].extend(file_changelog["Edited blocks"])

                # Handle CachedTagList: only include new tags not present in the master file's CachedTagList
                new_tags = set(json_data.get("CachedTagList", [])) - set(master_data.get("CachedTagList", []))
                if new_tags:
                    changelog[type_name].setdefault("CachedTagList", []).extend(sorted(new_tags))
                
                # Clean up intermediate files
                os.remove(json_file_path)
            else:
                print("There was an error when converting", file_name, "to JSON")
                sys.exit(1)
        else:
            decompressed_file_path = file_path[:-3]  # Remove .zs extension
            yaml_file_path = decompressed_file_path[:-4] + 'yaml'
            # Decompress and convert to YAML
            decompressor = Zstd()
            decompressor.Decompress(file_path, output_dir=folder_path, with_dict=True, no_output=False)
            process = subprocess.run([byml_to_yaml, "to-yaml", decompressed_file_path, "-o", yaml_file_path], capture_output=True, text=True)
            if "Command executed successfully" in process.stdout:
                # Find the most similar master file
                most_similar_master = find_most_similar_master(yaml_file_path)
                if most_similar_master is None:
                    print(f"No master found for {yaml_file_path}. Skipping this file.")
                    continue
                master_file_path = os.path.join(get_correct_path("master"), most_similar_master)
                print("Version detected:", most_similar_master[:-5])
                
                # Generate changelog
                file_changelog = generate_changelog_for_yaml(yaml_file_path, master_file_path)
                
                # Update the main changelog dictionary with the changes for this type
                changelog[type_name]["Added blocks"].extend(file_changelog["Added blocks"])
                changelog[type_name]["Edited blocks"].extend(file_changelog["Edited blocks"])
                # Clean up intermediate files
                os.remove(decompressed_file_path)
                os.remove(yaml_file_path)
            else:
                print("There was an error when converting", decompressed_file_path, "to YAML")
                sys.exit(1)
            
    # Check if the changelog is empty
    if any(changelog[type_name]["Added blocks"] or changelog[type_name]["Edited blocks"] for type_name in recognized_types):
        # Save the accumulated changelog to a single JSON file
        changelog_file_path = os.path.join(output_path, "rsdb.json")
        with open(changelog_file_path, 'w') as file:
            json.dump(changelog, file, indent=4)
        print("Changelog successfully generated")
    else:
        print("No changes detected. Changelog not generated.")

def apply_changelogs(changelog_dirs, version, output_dir):
    # List of recognized types
    recognized_types = [
        "ActorInfo.Product", "AttachmentActorInfo.Product", "Challenge.Product", "EnhancementMaterialInfo.Product",
        "EventPlayEnvSetting.Product", "EventSetting.Product", "GameActorInfo.Product", "GameAnalyzedEventInfo.Product",
        "GameEventBaseSetting.Product", "GameEventMetadata.Product", "GameSafetySetting.Product", "LoadingTips.Product",
        "Location.Product", "LocatorData.Product", "PouchActorInfo.Product", "Tag.Product", "TagDef.Product",
        "XLinkPropertyTable.Product", "XLinkPropertyTableList.Product"
    ]

    # Initialize an empty list to hold all changelog file paths
    all_changelog_files = []
    # Iterate over all provided directories
    # Aggregate all JSON changelog files from all provided directories
    for changelog_dir in changelog_dirs:
        if os.path.exists(changelog_dir):
            # Extend the list with all JSON files found in the current directory
            all_changelog_files.extend(glob.glob(os.path.join(changelog_dir, '*.json')))
        else:
            print(f"Warning: Changelog directory {changelog_dir} does not exist.")

    # Now, all_changelog_files contains paths to all changelog files across the provided directories
    # You can iterate over this list to process each changelog file
    for changelog_file in all_changelog_files:
        # Load the changelog
        with open(changelog_file, 'r') as f:
            changelog = json.load(f)

        # Check if if this is a RSDB changelog
        if not any(type in changelog for type in recognized_types):
            continue

        # Iterate over all recognized types in the changelog
        for recognized_type, changes in changelog.items():
            # Skip this recognized type if there are no edited blocks
            if not changes["Added blocks"] and not changes["Edited blocks"]:
                continue

            # Get the path to the master file for this recognized type
            master_file_path = os.path.join(master_dir, f'{recognized_type}.{version}.rstbl.yaml')
            output_file_path = os.path.join(output_dir, f'{recognized_type}.{version}.rstbl.yaml')

            # Create the output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

            if recognized_type == "Tag.Product":
                # Handle "Tag.Product" type as JSON
                master_file_path = master_file_path.replace('.yaml', '.byml.zs.json')
                output_file_path = output_file_path.replace('.yaml', '.byml.zs.json')

                # Load the master file if it exists, otherwise start with an empty dictionary
                if os.path.exists(output_file_path):
                    with open(output_file_path, 'r') as f:
                        master_data = json.load(f)
                elif os.path.exists(master_file_path):
                    with open(master_file_path, 'r') as f:
                        master_data = json.load(f)
                else:
                    master_data = {"ActorTagData": {}}

                # Apply edited blocks
                for block in changes["Edited blocks"]:
                    for actor, tags in block.items():
                        master_data["ActorTagData"][actor] = tags

                # Add new blocks
                for block in changes["Added blocks"]:
                    for actor, tags in block.items():
                        if actor not in master_data["ActorTagData"]:
                            master_data["ActorTagData"][actor] = tags

                # Update CachedTagList with new tags from the changelog, ensuring no duplicates and sorting alphanumerically
                new_tags = set(changes.get("CachedTagList", []))
                existing_tags = set(master_data.get("CachedTagList", []))
                updated_tags = sorted(existing_tags.union(new_tags))

                master_data["CachedTagList"] = updated_tags

                # Save the updated master data
                with open(output_file_path, 'w') as f:
                    json.dump(master_data, f, indent=4)
            else:
                # Load the master file if it exists, otherwise start with an empty list
                if os.path.exists(output_file_path):
                    with open(output_file_path, 'r', encoding='utf-8') as f:
                        master_data = f.readlines()
                elif os.path.exists(master_file_path):
                    with open(master_file_path, 'r', encoding='utf-8') as f:
                        master_data = f.readlines()
                else:
                    master_data = []

                # Process the master data and the temporary data
                master_blocks = {}
                temp_blocks = {}

                if recognized_type == "TagDef.Product":
                    for data, blocks in [(master_data, master_blocks), (changes["Edited blocks"], temp_blocks)]:
                        data_str = ''.join(data)
                        blocks_str = re.findall(r'{.*?}', data_str, re.DOTALL)
                        for block_str in blocks_str:
                            display_name_match = re.search(r'DisplayName: (.*?),', block_str)
                            if display_name_match:
                                display_name = display_name_match.group(1)
                                blocks[display_name] = block_str.split('\n')

                    # Replace the blocks in the master data with the blocks from the temporary data
                    for display_name, block in temp_blocks.items():
                        if display_name in master_blocks:
                            master_blocks[display_name] = block

                        # Convert the blocks in the master_blocks dictionary to a list and sort it by DisplayOrder
                        master_blocks_list = sorted(master_blocks.values(), key=lambda block: int(re.search(r'DisplayOrder: (\d+),', ''.join(block)).group(1)))

                        # Adjust the DisplayOrder values to ensure uniqueness
                        for i, block in enumerate(master_blocks_list):
                            block_str = ''.join(block)
                            block_str = re.sub(r'(DisplayOrder: )(\d+)', lambda m: m.group(1) + str(i), block_str)
                            master_blocks_list[i] = block_str.split('\n')

                        # Save the updated master data
                        with open(output_file_path, 'w') as f:
                            f.writelines('\n'.join('- ' + ''.join(block) for block in master_blocks_list))

                        added_blocks = []

                        # Process the added blocks
                        for block_str in changes["Added blocks"]:
                            # Remove leading '- ' from the block string
                            if block_str.startswith('- '):
                                block_str = block_str[2:]
                            # Extract the DisplayName from the block string
                            display_name_match = re.search(r'DisplayName: (.*?),', block_str)
                            if display_name_match:
                                display_name = display_name_match.group(1)
                                # If a block with the same DisplayName already exists, replace it
                                if display_name in master_blocks:
                                    master_blocks[display_name] = block_str.split('\n')
                                else:
                                    # If not, add the new block to the added_blocks list
                                    added_blocks.append(block_str)

                        # Append the added blocks to the end of the file
                        with open(output_file_path, 'a') as f:
                            for block_str in added_blocks:
                                f.write('\n- ' + block_str)

                        # Read the file again and adjust the DisplayOrder values
                        with open(output_file_path, 'r') as f:
                            lines = f.readlines()

                        with open(output_file_path, 'w') as f:
                            for i, line in enumerate(lines):
                                # Adjust the DisplayOrder value
                                line = re.sub(r'(DisplayOrder: )(\d+)', lambda m: m.group(1) + str(i), line)
                                f.write(line)

                        with open(output_file_path, 'a') as f:
                            f.writelines("\n")

                else:
                    # Define a dictionary that maps recognized_types to a corresponding regular expression
                    regex_dict = {
                        "GameSafetySetting.Product": r'!u 0x(.*?)(,|\n)',
                        "RumbleCall.Product": r',Name: (.*?)(})',
                        "UIScreen.Product": r'  Name: (.*?)(\n)',
                        "default": r'__RowId: (\S+)'
                    }

                    # Use the appropriate regular expression for each recognized_type
                    for data, blocks in [(master_data, master_blocks), (changes["Edited blocks"], temp_blocks)]:
                        data_str = ''.join(data)
                        blocks_str = re.findall(r'-.*?(?=\n-|$)', data_str, re.DOTALL)
                        for block_str in blocks_str:
                            regex = regex_dict.get(recognized_type, regex_dict["default"])
                            name_match = re.search(regex, block_str)
                            if name_match:
                                name = name_match.group(1)
                                if not block_str.endswith('\n'):
                                    block_str += "\n"
                                blocks[name] = block_str

                    # Replace the blocks in the master data with the blocks from the temporary data
                    for name, block in temp_blocks.items():
                        master_blocks[name] = block

                    # Save the updated master data
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        for i, block in enumerate(master_blocks.values()):
                            block_str = block
                            block_str = block_str.replace("- -", "-").replace("--", "-")
                            if i != 0 and not block_str.startswith('\n'):
                                block_str = '\n' + block_str
                            f.writelines(block_str)

                    added_blocks = []

                    # Process the added blocks
                    for block_str in changes["Added blocks"]:
                        # Remove leading '- ' from the block string
                        if block_str.startswith('- '):
                            block_str = block_str[2:]
                        name_match = re.search(regex, block_str)
                        if name_match:
                            name_hash = name_match.group(1)
                            # If a block with the same name hash already exists, replace it
                            if name_hash in master_blocks:
                                master_blocks[name_hash] = block_str
                            else:
                                # If not, add the new block to the added_blocks list
                                added_blocks.append(block_str)

                    # Append the added blocks to the end of the file
                    with open(output_file_path, 'a', encoding='utf-8') as f:
                        for block_str in added_blocks:
                            f.write('\n- ' + block_str)

                    with open(output_file_path, 'a', encoding='utf-8') as f:
                        f.writelines("\n")

    # After all changelogs have been processed, process each output file accordingly
    for output_file in glob.glob(os.path.join(output_dir, '*')):
        if output_file.endswith('.json'):
            # Process "Tag.Product" type with TagProductTool
            subprocess.run([tag_product, output_file, output_dir], capture_output=True, text=True)
            os.remove(output_file)
        elif output_file.endswith('.yaml'):
            # Convert other types to BYML, compress them, and delete the YAML files
            updated_byml_path = output_file[:-4] + 'byml'
            subprocess.call([byml_to_yaml, 'to-byml', output_file, '-o', updated_byml_path])
            
            # Compress the BYML file
            compressor = Zstd()
            compressor._CompressFile(updated_byml_path, output_dir=output_dir, level=16, with_dict=True)

            # Remove the uncompressed files
            os.remove(output_file)
            os.remove(updated_byml_path)

def process_and_merge_rsdb(mod_folder, version):
    temp_dir = tempfile.mkdtemp()
    rsdb_folders = []
    changelog_index = 0

    # Scan for every subfolder
    for root, dirs, files in os.walk(mod_folder):
        dirs.sort(reverse=True)  # Sort directories in reverse alphabetical order
        for dir_name in dirs:
            if dir_name == '00_MERGED_RSDB':
                continue
            rsdb_path = os.path.join(root, dir_name, 'romfs', 'RSDB')
            if os.path.exists(rsdb_path):
                rsdb_folders.append(rsdb_path)
                # Generate changelogs for each RSDB folder
                generate_changelogs(rsdb_path, temp_dir)
                # Rename rsdb.json to a numbered json file
                temp_json_path = os.path.join(temp_dir, 'rsdb.json')
                if os.path.exists(temp_json_path):
                    os.rename(os.path.join(temp_dir, 'rsdb.json'), os.path.join(temp_dir, f'{changelog_index}.json'))
                    changelog_index += 1

    # Create the merged RSDB folder
    merged_rsdb_folder = os.path.join(mod_folder, '00_MERGED_RSDB', 'romfs', 'RSDB')
    os.makedirs(merged_rsdb_folder, exist_ok=True)

    # Apply changelogs to the merged RSDB folder
    apply_changelogs([temp_dir], version, merged_rsdb_folder)

    # Remove the temporary directory
    for root, dirs, files in os.walk(temp_dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
    os.rmdir(temp_dir)

def parse_changelogs_to_files(changelog_json_path, output_directory):
    with open(changelog_json_path, 'r') as file:
        changelog = json.load(file)

    for product_type, changes in changelog.items():
        if changes.get("Added blocks") or changes.get("Edited blocks") or (product_type == "Tag.Product" and changes.get("CachedTagList")):
            if product_type == "Tag.Product":
                output_path = os.path.join(output_directory, f"{product_type}.json")
                with open(output_path, 'w') as json_file:
                    # Ensure all relevant sections are included for Tag.Product
                    data_to_write = {
                        "Added blocks": changes.get("Added blocks", []),
                        "Edited blocks": changes.get("Edited blocks", []),
                        "CachedTagList": changes.get("CachedTagList", [])
                    }
                    json.dump(data_to_write, json_file, indent=4)
            else:
                output_path = os.path.join(output_directory, f"{product_type}.yaml")
                with open(output_path, 'w') as text_file:
                    if changes.get("Added blocks"):
                        for block in changes["Added blocks"]:
                            text_file.write('{ADDITION}\n')  # Prepend ADDITION to each block
                            text_file.write(block + "\n")
                    if changes.get("Edited blocks"):
                        for block in changes["Edited blocks"]:
                            text_file.write('{MODIFICATION}\n')  # Prepend MODIFICATION to each block
                            text_file.write(block + "\n")

def pack_files_to_changelog(files_directory, output_json_path):
    recognized_types = [
        "ActorInfo.Product", "AttachmentActorInfo.Product", "Challenge.Product", "EnhancementMaterialInfo.Product",
        "EventPlayEnvSetting.Product", "EventSetting.Product", "GameActorInfo.Product", "GameAnalyzedEventInfo.Product",
        "GameEventBaseSetting.Product", "GameEventMetadata.Product", "GameSafetySetting.Product", "LoadingTips.Product",
        "Location.Product", "LocatorData.Product", "PouchActorInfo.Product", "RumbleCall.Product", "Tag.Product", 
        "TagDef.Product", "UIScreen.Product", "XLinkPropertyTable.Product", "XLinkPropertyTableList.Product"
    ]

    # Initialize the changelog dictionary with all recognized types
    changelog = {type_name: {"Added blocks": [], "Edited blocks": []} for type_name in recognized_types}

    for file_name in os.listdir(files_directory):
        product_type = file_name.split('.')[0]
        if not product_type.endswith(".Product"):
            product_type += ".Product"  # Ensure the product type ends with ".Product"

        file_path = os.path.join(files_directory, file_name)
        if file_name.endswith('.json'):
            with open(file_path, 'r') as file:
                changes = json.load(file)
                # Check and append \n to each block in the JSON data
                if "Added blocks" in changes:
                    changes["Added blocks"] = [block + "\n" if isinstance(block, str) else block for block in changes["Added blocks"]]
                if "Edited blocks" in changes:
                    changes["Edited blocks"] = [block + "\n" if isinstance(block, str) else block for block in changes["Edited blocks"]]
                
                # Include CachedTagList if it exists in the JSON data
                if "CachedTagList" in changes:
                    changes["CachedTagList"] = changes["CachedTagList"]  # Directly take the CachedTagList from the file

                changelog[product_type] = changes
        elif file_name.endswith('.yaml'):  # Assuming the extension is .yaml for plain text handling
            with open(file_path, 'r') as file:
                content = file.read()
                added_blocks = content.split('{ADDITION}\n')[1:]  # Split and remove the first part before the first {ADDITION}
                edited_blocks = content.split('{MODIFICATION}\n')[1:]  # Split and remove the first part before the first {MODIFICATION}

                # Process added blocks
                added_blocks = [block.strip() + "\n" for block in added_blocks if block.strip()]  # Append \n to each block
                # Process edited blocks
                edited_blocks = [block.strip() + "\n" for block in edited_blocks if block.strip()]  # Append \n to each block

                if added_blocks or edited_blocks:
                    changelog[product_type] = {"Added blocks": added_blocks, "Edited blocks": edited_blocks}
        else:
            continue

    with open(output_json_path, 'w') as file:
        json.dump(changelog, file, indent=4)

# GUI Application
ctk.set_appearance_mode("dark")
# Uncomment below line if compiling for switch
# ctk.set_widget_scaling(1.35)
class RSDBMergeApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title('RSDB Merge Tool 2.2')
        self.geometry('800x675')  # Adjusted for additional layout space
        if os.name == 'nt':
            self.iconbitmap(images)

        self.version_map = {
            '1.0.0': 100,
            '1.1.0': 110,
            '1.1.1': 111,
            '1.1.2': 112,
            '1.2.0': 120,
            '1.2.1': 121,
        }

        # Version selection
        # Container frame to hold the label and dropdown side by side
        container_frame = ctk.CTkFrame(self)
        container_frame.pack(fill='x', pady=5)
        container_frame.configure(fg_color=self.cget("fg_color"))
        inner_frame = ctk.CTkFrame(container_frame)
        inner_frame.pack(anchor='center')
        inner_frame.configure(fg_color=container_frame.cget("fg_color"))

        # Label for version selection
        version_label = ctk.CTkLabel(inner_frame, text="TotK Version:")
        version_label.pack(side='left', padx=(10, 0))

        # Dropdown menu for version selection
        self.version_var = ctk.StringVar(value="1.2.1")  # Default version set
        self.version_dropdown = ctk.CTkComboBox(inner_frame, values=list(self.version_map.keys()), variable=self.version_var, state="readonly")
        self.version_dropdown.pack(side='left', padx=(10, 10))

        # Merge Mods section
        self.setup_merge_mods_section()

        # Generate Changelog section
        self.setup_generate_changelog_section()

        # Apply Changelogs section
        self.setup_apply_changelogs_section()

        # Parse Changelogs section
        self.setup_changelog_processing_section()

        # Exit button
        self.setup_exit_button()

    def setup_section(self, frame, title, text_var, browse_command):
        entry_frame = ctk.CTkFrame(frame)
        entry_frame.pack(pady=5, fill='x', padx=20)
        
        # Match the background color of the parent frame
        entry_frame.configure(fg_color=frame.cget("fg_color"))
        
        # Set a fixed width for the label to ensure alignment
        label_width = 120  # Adjust this value as needed
        ctk.CTkLabel(entry_frame, text=title, width=label_width, anchor='w').pack(side='left', padx=(0, 10))
        
        # Set a fixed width for the entry to ensure consistent size
        entry_width = 450  # Adjust this value as needed
        ctk.CTkEntry(entry_frame, textvariable=text_var, width=entry_width).pack(side='left', fill='x', expand=True)
        
        ctk.CTkButton(entry_frame, text="Browse", command=browse_command).pack(side='left', padx=(10, 0))

    def setup_merge_mods_section(self):
        merge_mods_frame = ctk.CTkFrame(self)
        merge_mods_frame.pack(pady=5, fill='x')
        ctk.CTkLabel(merge_mods_frame, text="Merge Mods").pack()
        self.mod_path_var = ctk.StringVar()
        self.setup_section(merge_mods_frame, "Mod Folder:", self.mod_path_var, self.select_mod_path)
        ctk.CTkButton(merge_mods_frame, text="Merge", command=self.merge_mods).pack(pady=5)

    def select_mod_path(self):
        directory = fd.askdirectory()
        if directory:
            self.mod_path_var.set(directory)

    def merge_mods(self):
        # Convert the version to a string format expected by the function
        version_int = self.version_map[self.version_var.get()]
        process_and_merge_rsdb(self.mod_path_var.get(), version_int)
        messagebox.showinfo("Action Complete", "Mods merging completed")

    def setup_generate_changelog_section(self):
        generate_changelog_frame = ctk.CTkFrame(self)
        generate_changelog_frame.pack(pady=5, fill='x')
        ctk.CTkLabel(generate_changelog_frame, text="Generate Changelog").pack()
        self.rsdb_folder_var = ctk.StringVar()
        self.changelog_output_folder_var = ctk.StringVar()
        self.setup_section(generate_changelog_frame, "RSDB Folder:", self.rsdb_folder_var, self.select_rsdb_folder)
        self.setup_section(generate_changelog_frame, "Output Folder:", self.changelog_output_folder_var, self.select_changelog_output_folder)
        ctk.CTkButton(generate_changelog_frame, text="Generate", command=self.generate_changelog).pack(pady=5)

    def select_rsdb_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.rsdb_folder_var.set(directory)

    def select_changelog_output_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.changelog_output_folder_var.set(directory)

    def generate_changelog(self):
        generate_changelogs(self.rsdb_folder_var.get(), self.changelog_output_folder_var.get())
        messagebox.showinfo("Action Complete", "Changelog generated")

    def setup_apply_changelogs_section(self):
        apply_changelogs_frame = ctk.CTkFrame(self)
        apply_changelogs_frame.pack(pady=5, fill='x')
        ctk.CTkLabel(apply_changelogs_frame, text="Apply Changelogs").pack()
        self.changelog_folder_var = ctk.StringVar()
        self.output_rsdb_folder_var = ctk.StringVar()
        self.setup_section(apply_changelogs_frame, "Changelog Folder:", self.changelog_folder_var, self.select_changelog_folder)
        self.setup_section(apply_changelogs_frame, "Output RSDB Folder:", self.output_rsdb_folder_var, self.select_output_rsdb_folder)
        ctk.CTkButton(apply_changelogs_frame, text="Apply", command=self.apply_changelogs).pack(pady=5)

    def select_changelog_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.changelog_folder_var.set(directory)

    def select_output_rsdb_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.output_rsdb_folder_var.set(directory)

    def apply_changelogs(self):
        # Convert the version to a string format expected by the function
        version_str = str(self.version_map[self.version_var.get()])
        changelog_paths = self.changelog_folder_var.get().split('|')
        apply_changelogs(changelog_paths, version_str, self.output_rsdb_folder_var.get())
        messagebox.showinfo("Action Complete", "RSDB files generated at " + self.output_rsdb_folder_var.get())

    def setup_changelog_processing_section(self):
        changelog_processing_frame = ctk.CTkFrame(self)
        changelog_processing_frame.pack(pady=5, fill='x')
        ctk.CTkLabel(changelog_processing_frame, text="Changelog Processing").pack()
        
        self.processing_changelog_json_var = ctk.StringVar()
        self.setup_section(changelog_processing_frame, "JSON Changelog File:", self.processing_changelog_json_var, self.select_processing_changelog_json)
        
        self.processing_changelog_folder_var = ctk.StringVar()
        self.setup_section(changelog_processing_frame, "Parsed files folder:", self.processing_changelog_folder_var, self.select_processing_folder)
        
        # Frame for buttons, centered within the changelog_processing_frame
        button_frame = ctk.CTkFrame(changelog_processing_frame)
        button_frame.pack(pady=5)
        button_frame.configure(fg_color=changelog_processing_frame.cget("fg_color"))  # Match the background color

        # Buttons for parsing and packing changelogs
        parse_button = ctk.CTkButton(button_frame, text="Parse into files", command=self.parse_changelog_into_files)
        parse_button.pack(side='left', padx=10)
        
        pack_button = ctk.CTkButton(button_frame, text="Pack into changelog", command=self.pack_files_into_changelog)
        pack_button.pack(side='left', padx=10)

    def select_processing_changelog_json(self):
        file_path = fd.askopenfilename()
        if file_path:
            self.processing_changelog_json_var.set(file_path)

    def select_processing_folder(self):
        directory = fd.askdirectory()
        if directory:
            self.processing_changelog_folder_var.set(directory)

    def parse_changelog_into_files(self):
        parse_changelogs_to_files(self.processing_changelog_json_var.get(), self.processing_changelog_folder_var.get())
        messagebox.showinfo("Action Complete", "Changelog parsed into files")

    def pack_files_into_changelog(self):
        pack_files_to_changelog(self.processing_changelog_folder_var.get(), self.processing_changelog_json_var.get())
        messagebox.showinfo("Action Complete", "Files packed into changelog")

    def setup_exit_button(self):
        exit_button = ctk.CTkButton(self, text="Exit", command=self.destroy, width=135, height=40, fg_color='#C70039', hover_color='#E57373')
        # uncomment below line for Switch version
        #exit_button = ctk.CTkButton(self, text="Exit", command=self.destroy, width=135, height=60, fg_color='#C70039', hover_color='#E57373')
        exit_button.pack(side='right', anchor='e', padx=10, pady=1)

if __name__ == "__main__":
    # Check if any arguments were provided
    if len(sys.argv) == 1:
        # No arguments were provided, launch the GUI
        app = RSDBMergeApp()
        app.mainloop()
    else:
        # Arguments were provided, proceed with the CLI version
        parser = argparse.ArgumentParser(description='Merge or generate and apply changelogs for RSDB')
        parser.add_argument('--version', help='Version of TOTK for which to generate RSDB files (example: 121).')
        parser.add_argument('--merge', help='Path to the folder containing all of your mods')
        parser.add_argument('--generate-changelog', help='Path to the folder containing .byml.zs files to generate a changelog.')
        parser.add_argument('--apply-changelogs', help='Paths to the folders containing .json changelogs to apply.')
        parser.add_argument('--output', help='Path to the output directory for the generated changelog or for the generated RSDB files.')
        parser.add_argument('--parse-changelog', help='Path to the JSON changelog file to parse into multiple files.')
        parser.add_argument('--pack-changelog', help='Path to the folder containing parsed files to pack back into a JSON changelog.')
        parser.add_argument('--parse-output', help='Output directory for parsed files from the JSON changelog.')
        parser.add_argument('--pack-output', help='Output JSON file path for the packed changelog.')

        # Parse the arguments
        args = parser.parse_args()

        if args.merge:
            process_and_merge_rsdb(args.merge, args.version)

        if args.generate_changelog:
            output_path = args.output if args.output else os.path.dirname(os.path.abspath(__file__))
            generate_changelogs(args.generate_changelog, output_path)

        if args.apply_changelogs:
            if not (args.version and args.output):
                print("Error: --version and --output must be provided when using --apply-changelogs")
                sys.exit(1)
            changelog_paths = args.apply_changelogs.split('|')
            apply_changelogs(changelog_paths, args.version, args.output)

        if args.parse_changelog and args.parse_output:
            parse_changelogs_to_files(args.parse_changelog, args.parse_output)

        if args.pack_changelog and args.pack_output:
            pack_files_to_changelog(args.pack_changelog, args.pack_output)