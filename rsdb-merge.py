import os
import argparse
import subprocess
import sys
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

# Set up the argument parser
parser = argparse.ArgumentParser(description='Merge two .byml.zs files (RSDB only)')
parser.add_argument('--file1', required=True, help='Path to the first .byml.zs file.')
parser.add_argument('--file2', required=True, help='Path to the second .byml.zs file.')

# Parse the arguments
args = parser.parse_args()

# Get the directory of the byml.exe executable
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

# Use the application_path to define the output paths for the YAML files
yaml1 = os.path.join(application_path, "file1.yaml")
yaml2 = os.path.join(application_path, "file2.yaml")

# Get the absolute path
current_dir = os.path.dirname(os.path.abspath(__file__))
dist_path = "dist"
dist_path = get_correct_path(dist_path)
byml_to_yaml_exe = os.path.join(dist_path, "byml-to-yaml.exe")

# Convert the provided BYML files to YAML
decompressor = Zstd()
decompressor.Decompress(args.file1, output_dir=application_path, with_dict=True, no_output=False)
decompressed_file1_path = os.path.join(application_path, os.path.basename(args.file1)[:-3])  # Remove the .zs extension
decompressed_file1_path = get_correct_path(decompressed_file1_path)
decompressor.Decompress(args.file2, output_dir=application_path, with_dict=True, no_output=False)
decompressed_file2_path = os.path.join(application_path, os.path.basename(args.file2)[:-3])  # Remove the .zs extension
decompressed_file2_path = get_correct_path(decompressed_file2_path)

try:
    subprocess_output = subprocess.check_output(
        [byml_to_yaml_exe, "to-yaml", decompressed_file1_path, "-o", yaml1],
        stderr=subprocess.STDOUT
    )
except subprocess.CalledProcessError as e:
    print(f"Command failed with exit status {e.returncode}: {e.output.decode()}")

try:
    subprocess_output = subprocess.check_output(
        [byml_to_yaml_exe, "to-yaml", decompressed_file2_path, "-o", yaml2],
        stderr=subprocess.STDOUT
    )
except subprocess.CalledProcessError as e:
    print(f"Command failed with exit status {e.returncode}: {e.output.decode()}")

def find_last_row_id_chunk(file2_path):
    with open(file2_path, 'r') as file:
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

def find_most_similar_master(file1_path):
    master_dir = "master"
    master_dir = get_correct_path(master_dir)
    master_files = os.listdir(master_dir)
    master_files = [file for file in master_files if file.endswith('.yaml')]
    best_similarity = 0
    most_similar_master = None

    for master_file in master_files:
        master_path = os.path.join(master_dir, master_file)
        with open(file1_path, 'r') as file1, open(master_path, 'r') as master:
            file1_content = file1.read()
            master_content = master.read()
            similarity = similar_ratio(file1_content, master_content)
            if similarity > best_similarity:
                best_similarity = similarity
                most_similar_master = master_file

    return most_similar_master

def similar_ratio(a, b):
    return sum(1 for x, y in zip(a, b) if x == y) / max(len(a), len(b))

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

if __name__ == "__main__":
    most_similar_master = find_most_similar_master("file1.yaml")
    master_dir = "master"
    master_dir = get_correct_path(master_dir)
    if most_similar_master:
        master_path = os.path.join(master_dir, most_similar_master)
        master_file_name_without_extension = os.path.splitext(most_similar_master)[0]
        print(f"Using version: {master_file_name_without_extension}")
    else:
        print('No master found!')
        exit()
    file1_path = "file1.yaml"
    file2_path = "file2.yaml"
    yaml_files = ["file1.yaml", "file2.yaml"]
    output_yaml = "merged.yaml"

    last_row_id = find_last_row_id_chunk(file2_path)
    merge_yaml_files(yaml_files, output_yaml, master_path)

    file = open('merged.yaml', 'a')
    #file.writelines(last_row_id)
    file.close()

    for yaml_file in yaml_files:
        if os.path.exists(yaml_file):
            os.remove(yaml_file)

    merged_byml_path = os.path.join(application_path, "merged.byml")

    try:
        subprocess_output = subprocess.check_output(
            [byml_to_yaml_exe, "to-byml", "merged.yaml", "-o", merged_byml_path],
            stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit status {e.returncode}: {e.output.decode()}")

    # Initialize the Zstd compressor
    output_compressed_path = merged_byml_path + ".zs"
    compressor = Zstd()

    # Compress the merged.byml file
    compressor._CompressFile(merged_byml_path, output_dir='', level=16, with_dict=True)

    # Clean up the intermediate files
    os.remove(merged_byml_path)
    bylm1_path = "file1.byml"
    byml2_path = "file2.byml"
    os.remove(bylm1_path)
    os.remove(byml2_path)

    print(f"Compressed file outputted as: {output_compressed_path}")

    os.remove(output_yaml)

    print("Tasks completed successfully!")
