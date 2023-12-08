import os
import json
import yaml
import glob
import argparse
import subprocess
import sys
from zstd import Zstd

def ul_constructor(loader, node):
    return int(node.value)

yaml.SafeLoader.add_constructor('!ul', ul_constructor)

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
master_dir = "master"
master_dir = get_correct_path(master_dir)

def find_last_row_id_chunk(yaml2):
    with open(yaml2, 'r') as file:
        lines = file.readlines()

    last_row_id_chunk = []
    row_id_count = 0

    for line in reversed(lines):
        if "  __RowId:" in line:
            row_id_count += 1
            if row_id_count == 2:
                break
        if row_id_count == 1:
            last_row_id_chunk.append(line)

    last_row_id_chunk.reverse()
    last_row_id = ''.join(last_row_id_chunk).strip()

    return last_row_id

def count_common_lines(file_content, master_content):
    # Split the file content into lines and use sets for quick comparison
    file_lines = set(file_content.splitlines())
    master_lines = set(master_content.splitlines())
    # Count the number of common lines
    common_lines = file_lines.intersection(master_lines)
    return len(common_lines)

def find_most_similar_master(yaml1):
    master_dir = "master"
    master_dir = get_correct_path(master_dir)
    master_files = os.listdir(master_dir)
    master_files = [file for file in master_files if file.endswith('.yaml')]
    
    with open(yaml1, 'r') as file1:
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

def custom_merge(master_data, data1, data2):
    result = []
    index1 = 0
    index2 = 0
    master_index = 0

    while index1 < len(data1) and index2 < len(data2):
        block_master = []
        block_data1 = []
        block_data2 = []

        # Collect the block from the master data
        while master_index < len(master_data) and "__RowId:" not in master_data[master_index]:
            block_master.append(master_data[master_index])
            master_index += 1
        if master_index < len(master_data):
            block_master.append(master_data[master_index])

        # Collect the block from data1
        while index1 < len(data1) and "__RowId:" not in data1[index1]:
            block_data1.append(data1[index1])
            index1 += 1
        if index1 < len(data1):
            block_data1.append(data1[index1])

        # Collect the block from data2
        while index2 < len(data2) and "__RowId:" not in data2[index2]:
            block_data2.append(data2[index2])
            index2 += 1
        if index2 < len(data2):
            block_data2.append(data2[index2])

        # Check if the __RowId line is the same in all three blocks
        same_row_id_all = (block_data1[-1] == block_master[-1] and block_data2[-1] == block_master[-1])
        added_in_data1 = block_data1[-1] != block_master[-1]
        added_in_data2 = block_data2[-1] != block_master[-1]

        # Prioritize block from file1 unless it's identical to the master's, then use file2's
        if same_row_id_all:
            if block_data1 != block_master:
                result.extend(block_data1)
            else:
                result.extend(block_data2)
            master_index += 1
            index1 += 1
            index2 += 1
        # If the __RowId line differs, consider it an added block
        elif added_in_data1 and not added_in_data2:
            result.extend(block_data1)
            index1 += 1  # Move to the next block in data1
        elif not added_in_data1 and added_in_data2:
            result.extend(block_data2)
            index2 += 1  # Move to the next block in data2
        elif added_in_data1 and added_in_data2:
            # Both file1 and file2 have added blocks, add both
            result.extend(block_data1)
            result.extend(block_data2)
            index1 += 1
            index2 += 1
            # Do not increment master_index because both blocks were added

    # Append any remaining blocks from data1 or data2 that weren't processed
    while index1 < len(data1):
        result.append(data1[index1])
        index1 += 1
    while index2 < len(data2):
        result.append(data2[index2])
        index2 += 1

    return result

def merge_yaml_files(yaml_files, output_yaml, master_yaml):
    with open(master_yaml, 'r') as master_file:
        master_data = master_file.readlines()

    if len(yaml_files) != 2:
        print("Error: merge_yaml_files requires exactly 2 yaml files")
        return

    with open(yaml_files[0], 'r') as file1:
        data1 = file1.readlines()

    with open(yaml_files[1], 'r') as file2:
        data2 = file2.readlines()

    merged_data = custom_merge(master_data, data1, data2)

    with open(output_yaml, 'w') as file:
        file.writelines(merged_data)

def generate_changelog_for_file(yaml_file_path, master_file_path):
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
            master_blocks[line] = block_master
            block_master = []

    # Process each block in yaml_data
    block_yaml = []
    for line in yaml_data:
        block_yaml.append(line)
        if "__RowId:" in line:
            if line in master_blocks:
                # Compare the entire block, not just the __RowId line
                if ''.join(block_yaml) != ''.join(master_blocks[line]):
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
        "ActorInfo", "AttachmentActorInfo", "Challenge", "EnhancementMaterialInfo",
        "EventPlayEnvSetting", "EventSetting", "GameActorInfo", "GameAnalyzedEventInfo",
        "GameEventBaseSetting", "GameEventMetadata", "LocatorData", "PouchActorInfo",
        "XLinkPropertyTableList"
    ]

    # Initialize changelog dictionary with sections for each type
    changelog = {type_name: {"Added blocks": [], "Edited blocks": []} for type_name in recognized_types}

    # Dictionary to hold the latest version file for each type
    latest_files = {}

    # Identify the latest version file for each type
    for file_name in os.listdir(folder_path):
        for type_name in recognized_types:
            if file_name.startswith(type_name) and file_name.endswith('.byml.zs'):
                version = int(file_name.split('.')[2])  # Assuming version is always an integer
                if type_name not in latest_files or version > latest_files[type_name][1]:
                    latest_files[type_name] = (file_name, version)

    # Decompress and convert .byml.zs files
    for type_name, (file_name, version) in latest_files.items():
        if file_name.startswith(tuple(recognized_types)) and file_name.endswith('.byml.zs'):
            decompressed_file_path = os.path.join(folder_path, file_name[:-3])  # Remove .zs extension
            yaml_file_path = decompressed_file_path[:-4] + 'yaml'
            # Decompress and convert to YAML
            decompressor = Zstd()
            decompressor.Decompress(os.path.join(folder_path, file_name), output_dir=folder_path, with_dict=True, no_output=False)
            subprocess.call([byml_to_yaml_exe, "to-yaml", decompressed_file_path, "-o", yaml_file_path])
            
            # Find the most similar master file
            most_similar_master = find_most_similar_master(yaml_file_path)
            master_file_path = os.path.join(get_correct_path("master"), most_similar_master)
            
            # Generate changelog
            file_changelog = generate_changelog_for_file(yaml_file_path, master_file_path)
            
            # Update the main changelog dictionary with the changes for this type
            changelog[type_name]["Added blocks"].extend(file_changelog["Added blocks"])
            changelog[type_name]["Edited blocks"].extend(file_changelog["Edited blocks"])

            # Clean up intermediate files
            os.remove(decompressed_file_path)
            os.remove(yaml_file_path)

    # Save the accumulated changelog to a single JSON file
    changelog_file_path = os.path.join(output_path, "changelog.json")
    with open(changelog_file_path, 'w') as file:
        json.dump(changelog, file, indent=4)

def apply_changelogs(changelog_dir, version, output_dir):
    # Get the list of all JSON files in the directory
    changelog_files = glob.glob(os.path.join(changelog_dir, '*.json'))

    # Iterate over all JSON files
    for changelog_file in changelog_files:
        # Load the changelog
        with open(changelog_file, 'r') as f:
            changelog = json.load(f)

        # Iterate over all recognized types in the changelog
        for recognized_type, changes in changelog.items():
            # Skip this recognized type if there are no edited blocks
            if not changes["Added blocks"] and not changes["Edited blocks"]:
                continue

            # Get the path to the master file for this recognized type
            master_file_path = os.path.join(master_dir, f'{recognized_type}.Product.{version}.rstbl.yaml')
            output_file_path = os.path.join(output_dir, f'{recognized_type}.Product.{version}.rstbl.yaml')

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
    # Create a Zstd compressor
    compressor = Zstd()

    # After all changelogs have been processed, convert all the output YAML files to BYML, compress them, and delete the YAML files
    for output_file in glob.glob(os.path.join(output_dir, '*.yaml')):
        updated_byml_path = output_file[:-4] + 'byml'
        subprocess.call([byml_to_yaml_exe, 'to-byml', output_file, '-o', updated_byml_path])
        
        # Compress the BYML file
        compressor._CompressFile(updated_byml_path, output_dir=output_dir, level=16, with_dict=True)

        # Remove the uncompressed files
        os.remove(output_file)
        os.remove(updated_byml_path)

# Set up the argument parser
parser = argparse.ArgumentParser(description='Generate and apply changelogs for RSDB')
parser.add_argument('--generate-changelog', help='Path to the folder containing .byml.zs files to generate changelogs.')
parser.add_argument('--output', help='Output path for the generated changelog or for the generated RSDB files.')
parser.add_argument('--apply-changelogs', help='Path to the folder containing .json changelogs to apply.')
parser.add_argument('--version', help='Version of the master file to use as a base.')

# Parse the arguments
args = parser.parse_args()

if args.generate_changelog:
    output_path = args.output if args.output else os.path.dirname(os.path.abspath(__file__))
    generate_changelogs(args.generate_changelog, output_path)

if args.apply_changelogs:
    if not (args.version and args.output):
        print("Error: --version and --output must be provided when using --apply-changelogs")
        sys.exit(1)
    apply_changelogs(args.apply_changelogs, args.version, args.output)
