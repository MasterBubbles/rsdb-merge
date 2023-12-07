try:
    import zstandard as zs
except ImportError:
    raise ImportError("Would you be so kind as to LEARN TO FUCKING READ INSTRUCTIONS")
import sarc
import os
import io
import sys

def get_correct_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class Zstd:
    # Initialize decompressor
    def __init__(self, format=zs.FORMAT_ZSTD1): # zs.FORMAT_ZSTD1_MAGICLESS for headerless
        self.format = format
        zsdic_dir = "dic/ZsDic.pack.zs"
        zsdic_dir = get_correct_path(zsdic_dir)
        self.decompressor = zs.ZstdDecompressor()
        with open(os.path.join(zsdic_dir), 'rb') as file:
            data = file.read()
        self.dictionaries = self.decompressor.decompress(data)
        self.dictionaries = sarc.Sarc(self.dictionaries)
        self.dictionaries = self.dictionaries.files

    # Decompresses specified file to specified location
    def _DecompressFile(self, filepath, output_dir='', with_dict=False, no_output=False):
        if with_dict and os.path.basename(filepath) != 'ZsDic.pack.zs':
            if os.path.splitext(os.path.splitext(filepath)[0])[1] == '.pack':
                for dic in self.dictionaries:
                    if dic["Name"] == 'pack.zsdic':
                        dictionary = dic["Data"]
                        break
            elif os.path.splitext(os.path.splitext(filepath)[0])[1] == '.byml':
                if os.path.splitext(os.path.splitext(os.path.splitext(filepath)[0])[0])[1] == '.bcett':
                    for dic in self.dictionaries:
                        if dic["Name"] == 'bcett.byml.zsdic':
                            dictionary = dic["Data"]
                            break
                else:
                    for dic in self.dictionaries:
                        if dic["Name"] == 'zs.zsdic':
                            dictionary = dic["Data"]
                            break
            else:
                for dic in self.dictionaries:
                    if dic["Name"] == 'zs.zsdic':
                        dictionary = dic["Data"]
                        break
            self.decompressor = zs.ZstdDecompressor(zs.ZstdCompressionDict(dictionary), format=self.format)
        else:
            self.decompressor = zs.ZstdDecompressor(format=self.format)
        with open(filepath, 'rb') as file:
            data = file.read()
        decompressed_data = self.decompressor.decompress(data)
        if not no_output:
            # Remove the .zs extension from the filename
            output_filename = os.path.basename(filepath)
            if output_filename.lower().endswith('.zs'):
                output_filename = output_filename[:-3]

            output_path = os.path.join(output_dir, output_filename)
            try:
                with open(output_path, 'wb') as file:
                    file.write(decompressed_data)
            except Exception as e:
                print(f"Failed to write decompressed data to {output_path}: {e}")

    # Decompresses a file or directory
    def Decompress(self, filepath, output_dir='', with_dict=True, no_output=False):
        if os.path.isfile(filepath):
            return self._DecompressFile(filepath, output_dir, with_dict, no_output)
        elif os.path.isdir(filepath):
            for root_dir, dir, files in os.walk(filepath):
                for file in files:
                    if os.path.isfile(os.path.join(root_dir, file)):
                        rel_path = os.path.relpath(root_dir, filepath)
                        if not(os.path.exists(os.path.join(output_dir, rel_path))):
                            os.makedirs(os.path.join(output_dir, rel_path))
                        return self._DecompressFile(os.path.join(root_dir, file), os.path.join(output_dir, rel_path), with_dict, no_output)

    # Get size of decompressed file
    def GetDecompressedSize(self, filepath, with_dict=True):
        with open(filepath, 'rb') as file:
            if os.path.splitext(filepath)[1] in ['.zs', '.zstd']:
                if os.path.splitext(filepath)[1] == '.mc':
                    file.seek(0xc)
                data = file.read()
                if with_dict:
                    if os.path.splitext(os.path.splitext(filepath)[0])[1] == '.pack':
                        for dic in self.dictionaries:
                            if dic["Name"] == 'pack.zsdic':
                                dictionary = dic["Data"]
                                break
                    elif os.path.splitext(os.path.splitext(filepath)[0])[1] == '.byml':
                        if os.path.splitext(os.path.splitext(os.path.splitext(filepath)[0])[0])[1] == '.bcett':
                            for dic in self.dictionaries:
                                if dic["Name"] == 'bcett.byml.zsdic':
                                    dictionary = dic["Data"]
                                    break
                        else:
                            for dic in self.dictionaries:
                                if dic["Name"] == 'zs.zsdic':
                                    dictionary = dic["Data"]
                                    break
                    else:
                        for dic in self.dictionaries:
                            if dic["Name"] == 'zs.zsdic':
                                dictionary = dic["Data"]
                                break
                    self.decompressor = zs.ZstdDecompressor(zs.ZstdCompressionDict(dictionary), format=self.format)
                else:
                    self.decompressor = zs.ZstdDecompressor(format=self.format)
                return len(self.decompressor.decompress(data))
            else:
                file.seek(0, io.SEEK_END)
                return file.tell()

    # Compresses file to specified location
    def _CompressFile(self, filepath, output_dir='', level=16, with_dict=False):
        if with_dict and os.path.basename(filepath) != 'ZsDic.pack.zs':
            if os.path.splitext(os.path.splitext(filepath)[0])[1] == '.pack':
                for dic in self.dictionaries:
                    if dic["Name"] == 'pack.zsdic':
                        dictionary = dic["Data"]
                        break
            elif os.path.splitext(os.path.splitext(filepath)[0])[1] == '.byml':
                if os.path.splitext(os.path.splitext(os.path.splitext(filepath)[0])[0])[1] == '.bcett':
                    for dic in self.dictionaries:
                        if dic["Name"] == 'bcett.byml.zsdic':
                            dictionary = dic["Data"]
                            break
            else:
                for dic in self.dictionaries:
                    if dic["Name"] == 'zs.zsdic':
                        dictionary = dic["Data"]
                        break
            self.compressor = zs.ZstdCompressor(level, zs.ZstdCompressionDict(dictionary))
        else:
            self.compressor = zs.ZstdCompressor(level)
        with open(filepath, 'rb') as file:
            data = file.read()
        filepath += '.zs'
        with open(os.path.join(output_dir, os.path.basename(filepath)), 'wb') as file:
            if self.format == zs.FORMAT_ZSTD1_MAGICLESS:
                file.write(self.compressor.compress(data)[4:])
                return self.compressor.compress(data)[4:]
            else:
                file.write(self.compressor.compress(data))
                return self.compressor.compress(data)
    
    # Compresses file or files and maintains directory structure
    def Compress(self, filepath, output_dir='', level=16, with_dict=True):
        if os.path.isfile(filepath):
            return self._CompressFile(filepath, output_dir, level, with_dict)
        elif os.path.isdir(filepath):
            for root_dir, dir, files in os.walk(filepath):
                for file in files:
                    if os.path.isfile(os.path.join(root_dir, file)):
                        rel_path = os.path.relpath(root_dir, filepath)
                        if not(os.path.exists(os.path.join(output_dir, rel_path))):
                            os.makedirs(os.path.join(output_dir, rel_path))
                        return self._CompressFile(os.path.join(root_dir, file), os.path.join(output_dir, rel_path), level, with_dict)