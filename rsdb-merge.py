import os
import json
import glob
import argparse
import subprocess
import sys
from zstd import Zstd
import yaml

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
byml_to_yaml_exe = os.path.join(dist_path, "byml-to-yaml.exe")
tag_product_exe = os.path.join(dist_path, "TagProductTool.exe")
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
    # Split the file content into blocks
    file_blocks = set(file_content.split("__RowId:"))
    master_blocks = set(master_content.split("__RowId:"))
    # Count the number of identical blocks
    identical_block_count = len(file_blocks & master_blocks)
    return identical_block_count

def count_common_blocks_misc(file_content, master_content):
    # Split the file content into blocks and strip any leading or trailing whitespaces
    file_blocks = set(block.strip() for block in file_content.split('}\n'))
    master_blocks = set(block.strip() for block in master_content.split('}\n'))
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

    if compared_file_prefix in ["TagDef.Product", "GameSafetySetting.Product"]:
        count_common_blocks_func = count_common_blocks_misc
    else:
        count_common_blocks_func = count_common_blocks

    # Filter the master_files based on the prefix
    master_files = [file for file in master_files if file.startswith(compared_file_prefix) and file.endswith('.yaml')]
    
    with open(compared_file, 'r') as file1:
        file1_content = file1.read()

    best_match_count = 0
    most_similar_master = None

    for master_file in master_files:
        master_path = os.path.join(master_dir, master_file)
        with open(master_path, 'r') as master:
            master_content = master.read()
            common_block_count = count_common_blocks_func(file1_content, master_content)
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

import re

def generate_changelog_misc(file_path, master_file_path):
    # Load the file and master data
    with open(file_path, 'r') as file:
        file_data = [block + '}' for block in file.read().split('}\n') if block]
    with open(master_file_path, 'r') as master_file:
        master_data = [block + '}' for block in master_file.read().split('}\n') if block]

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
    else:
        print(f"Unrecognized file name: {file_name}")
        return None

    # Process each block in file_data
    for block in file_data:
        match = re.search(f'{identifier}: (.*?)[,}}]', block)
        if match:
            value = match.group(1)
            master_block = next((block for block in master_data if re.search(f'{identifier}: {value}[,}}]', block)), None)
            if master_block is None:
                # Block is added
                changelog["Added blocks"].append(block)
                print(block)
            else:
                # Sort the lines in the blocks before comparison
                block_sorted = '\n'.join(sorted(block.split('\n')))
                master_block_sorted = '\n'.join(sorted(master_block.split('\n')))
                if block_sorted.strip() != master_block_sorted.strip():
                    # Block is edited
                    changelog["Edited blocks"].append(block)
                    print(block)

    return changelog

def generate_changelog_for_yaml(yaml_file_path, master_file_path):
    with open(yaml_file_path, 'r') as file:
        yaml_data = file.readlines()
    
    with open(master_file_path, 'r') as file:
        master_data = file.readlines()
    
    changelog = {
        "Added blocks": [],
        "Edited blocks": []
    }

    # Create a dictionary to map __RowId lines to blocks in master_data
    master_blocks = {}
    block_master = []
    for line in master_data:
        block_master.append(line)
        if "__RowId:" in line:
            row_id = line.split("__RowId:")[1].strip()  # Get the part of the line after "__RowId:"
            master_blocks[row_id] = block_master
            block_master = []

    # Process each block in yaml_data
    block_yaml = []
    for line in yaml_data:
        block_yaml.append(line)
        if "__RowId:" in line:
            row_id = line.split("__RowId:")[1].strip()  # Get the part of the line after "__RowId:"
            if row_id in master_blocks:
                # Compare the entire block, not just the __RowId line
                if ''.join(block_yaml) != ''.join(master_blocks[row_id]):
                    # Block is edited
                    changelog["Edited blocks"].append(''.join(block_yaml))
            else:
                # Block is added
                changelog["Added blocks"].append(''.join(block_yaml))
            block_yaml = []  # Reset block for the next one

    return changelog

def generate_changelogs(folder_path, output_path):
    # List of recognized types
    recognized_types = [
        "ActorInfo.Product", "AttachmentActorInfo.Product", "Challenge.Product", "EnhancementMaterialInfo.Product",
        "EventPlayEnvSetting.Product", "EventSetting.Product", "GameActorInfo.Product", "GameAnalyzedEventInfo.Product",
        "GameEventBaseSetting.Product", "GameEventMetadata.Product", "GameSafetySetting.Product", "LoadingTips.Product",
        "Location.Product", "LocatorData.Product", "PouchActorInfo.Product", "Tag.Product", "TagDef.Product",
        "XLinkPropertyTable.Product", "XLinkPropertyTableList.Product"
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
            process = subprocess.run([tag_product_exe, os.path.join(folder_path, file_name), folder_path], capture_output=True, text=True)
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
            process = subprocess.run([byml_to_yaml_exe, "to-yaml", decompressed_file_path, "-o", yaml_file_path], capture_output=True, text=True)
            if "Command executed successfully" in process.stdout:
                # Find the most similar master file
                most_similar_master = find_most_similar_master(yaml_file_path)
                if most_similar_master is None:
                    print(f"No master found for {yaml_file_path}. Skipping this file.")
                    continue
                master_file_path = os.path.join(get_correct_path("master"), most_similar_master)
                print("Version detected:", most_similar_master[:-5])
                
                # Generate changelog
                if type_name in ["TagDef.Product", "GameSafetySetting.Product"]:
                    generate_changelog_func = generate_changelog_misc
                else:
                    generate_changelog_func = generate_changelog_for_yaml
                file_changelog = generate_changelog_func(yaml_file_path, master_file_path)
                
                # Update the main changelog dictionary with the changes for this type
                changelog[type_name]["Added blocks"].extend(file_changelog["Added blocks"])
                changelog[type_name]["Edited blocks"].extend(file_changelog["Edited blocks"])
                # Clean up intermediate files
                os.remove(decompressed_file_path)
                os.remove(yaml_file_path)
            else:
                print("There was an error when converting", decompressed_file_path, "to YAML")
                sys.exit(1)
            
    # Save the accumulated changelog to a single JSON file
    changelog_file_path = os.path.join(output_path, "rsdb.json")
    with open(changelog_file_path, 'w') as file:
        json.dump(changelog, file, indent=4)
    print("Changelog successfully generated at:", changelog_file_path)

def apply_changelogs(changelog_dirs, version, output_dir):
    # List of recognized types
    recognized_types = [
        "ActorInfo.Product", "AttachmentActorInfo.Product", "Challenge.Product", "EnhancementMaterialInfo.Product",
        "EventPlayEnvSetting.Product", "EventSetting.Product", "GameActorInfo.Product", "GameAnalyzedEventInfo.Product",
        "GameEventBaseSetting.Product", "GameEventMetadata.Product", "GameSafetySetting.Product", "LoadingTips.Product",
        "Location.Product", "LocatorData.Product", "PouchActorInfo.Product", "Tag.Product", "TagDef.Product",
        "XLinkPropertyTable.Product", "XLinkPropertyTableList.Product"
    ]
    # Iterate over all provided directories
    for changelog_dir in changelog_dirs:
        # Get the list of all JSON files in the directory
        changelog_files = glob.glob(os.path.join(changelog_dir, '*.json'))

        # Iterate over all JSON files
        for changelog_file in changelog_files:
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

                    # Save the updated master data
                    with open(output_file_path, 'w') as f:
                        json.dump(master_data, f, indent=4)
                else:
                    # Load the master file if it exists, otherwise start with an empty list
                    if os.path.exists(output_file_path):
                        with open(output_file_path, 'r') as f:
                            master_data = f.readlines()
                    elif os.path.exists(master_file_path):
                        with open(master_file_path, 'r') as f:
                            master_data = f.readlines()
                    else:
                        master_data = []

                    # Create a temporary YAML file for the edited blocks
                    temp_yaml_path = os.path.join(output_dir, 'temp.yaml')
                    with open(temp_yaml_path, 'w') as f:
                        for block_str in changes["Edited blocks"]:
                            f.write(block_str)

                    # Load the temporary YAML file
                    with open(temp_yaml_path, 'r') as f:
                        temp_data = f.readlines()

                    # Remove the temporary YAML file
                    os.remove(temp_yaml_path)

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

                    elif recognized_type == "GameSafetySetting.Product":
                        for data, blocks in [(master_data, master_blocks), (changes["Edited blocks"], temp_blocks)]:
                            data_str = ''.join(data)
                            blocks_str = re.findall(r'{.*?}', data_str, re.DOTALL)
                            for block_str in blocks_str:
                                name_hash_match = re.search(r'NameHash: (.*?)[,}]', block_str)
                                if name_hash_match:
                                    name_hash = name_hash_match.group(1)
                                    blocks[name_hash] = block_str.split('\n')

                        # Replace the blocks in the master data with the blocks from the temporary data
                        for name_hash, block in temp_blocks.items():
                            if name_hash in master_blocks:
                                master_blocks[name_hash] = block

                        # Save the updated master data
                        with open(output_file_path, 'w') as f:
                            for i, block in enumerate(master_blocks.values()):
                                block_str = "- " + '\n'.join(block)
                                # If it's not the last block, add a newline at the end
                                if i < len(master_blocks) - 1:
                                    block_str += "\n"
                                f.writelines(block_str)

                        added_blocks = []

                        # Process the added blocks
                        for block_str in changes["Added blocks"]:
                            # Remove leading '- ' from the block string
                            if block_str.startswith('- '):
                                block_str = block_str[2:]
                            # Extract the name hash from the block string
                            name_hash_match = re.search(r'NameHash: (.*?)[,}]', block_str)
                            if name_hash_match:
                                name_hash = name_hash_match.group(1)
                                # If a block with the same name hash already exists, replace it
                                if name_hash in master_blocks:
                                    master_blocks[name_hash] = block_str.split('\n')
                                else:
                                    # If not, add the new block to the added_blocks list
                                    added_blocks.append(block_str)

                        # Append the added blocks to the end of the file
                        with open(output_file_path, 'a') as f:
                            for block_str in added_blocks:
                                f.write('\n- ' + block_str)

                        with open(output_file_path, 'a') as f:
                            f.writelines("\n")

                    else:
                        for data, blocks in [(master_data, master_blocks), (temp_data, temp_blocks)]:
                            block = []
                            for line in data:
                                block.append(line)
                                if "__RowId:" in line:
                                    row_id = line.split("__RowId:")[1].strip()
                                    blocks[row_id] = block
                                    block = []

                        # Replace the blocks in the master data with the blocks from the temporary data
                        for row_id, block in temp_blocks.items():
                            if row_id in master_blocks:
                                master_blocks[row_id] = block

                        # Save the updated master data
                        with open(output_file_path, 'w') as f:
                            for block in master_blocks.values():
                                f.writelines(block)

                        # Append the added blocks to the end of the file
                        with open(output_file_path, 'a') as f:
                            for block_str in changes["Added blocks"]:
                                f.write(block_str)

        # After all changelogs have been processed, process each output file accordingly
        for output_file in glob.glob(os.path.join(output_dir, '*')):
            if output_file.endswith('.json'):
                # Process "Tag.Product" type with tag_product_exe
                subprocess.run([tag_product_exe, output_file, output_dir], capture_output=True, text=True)
                os.remove(output_file)
            elif output_file.endswith('.yaml'):
                # Convert other types to BYML, compress them, and delete the YAML files
                updated_byml_path = output_file[:-4] + 'byml'
                subprocess.call([byml_to_yaml_exe, 'to-byml', output_file, '-o', updated_byml_path])
                
                # Compress the BYML file
                compressor = Zstd()
                compressor._CompressFile(updated_byml_path, output_dir=output_dir, level=16, with_dict=True)

                # Remove the uncompressed files
                os.remove(output_file)
                os.remove(updated_byml_path)

# Set up the argument parser
parser = argparse.ArgumentParser(description='Generate and apply changelogs for RSDB')
parser.add_argument('--generate-changelog', help='Path to the folder containing .byml.zs files to generate changelogs.')
parser.add_argument('--apply-changelogs', help='Paths to the folders containing .json changelogs to apply.')
parser.add_argument('--output', help='Path to the output directory for the generated changelog or for the generated RSDB files.')
parser.add_argument('--version', help='Version of TOTK for which to generate RSDB files (example: 121).')

# Parse the arguments
args = parser.parse_args()

if args.generate_changelog:
    output_path = args.output if args.output else os.path.dirname(os.path.abspath(__file__))
    generate_changelogs(args.generate_changelog, output_path)

if args.apply_changelogs:
    if not (args.version and args.output):
        print("Error: --version and --output must be provided when using --apply-changelogs")
        sys.exit(1)
    changelog_paths = args.apply_changelogs.split('|')
    apply_changelogs(changelog_paths, args.version, args.output)
