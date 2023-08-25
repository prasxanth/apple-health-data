import os
import datetime
import shutil
import json
import random
import string
import deflate
import zstandard
import snappy
import lzo
from typing import Union, Optional
from pathlib import Path
from inflection import underscore, dasherize

from apple_health_data.core.logger import VerbosityLogger

def remove_filename_extensions(filename, count=None, remove_all=False):
    parts = filename.split('.')
    
    if remove_all:
        return parts[0]
    elif count is not None and count > 0 and len(parts) > 1:
        return remove_filename_extensions('.'.join(parts[:-1]), count - 1)
    else:
        return filename


def create_folder(
    folder_path: Path, vlogger: VerbosityLogger = VerbosityLogger()
) -> None:
    if folder_path.exists():
        return vlogger.info(f"Folder {folder_path} already exists.", 1)
    else:
        try:
            folder_path.mkdir(parents=True)
            vlogger.info(f"{folder_path} created successfully.", 1)
        except OSError as e:
            vlogger.error(f"Failed to create {folder_path}: {e}", 1)


def get_last_modified_date(
    file_path: Path, vlogger: VerbosityLogger = VerbosityLogger()
) -> str:
    if file_path.exists():
        timestamp = file_path.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp)
        date_string = dt.strftime("%Y-%m-%d")
        return date_string
    else:
        vlogger.error(f"File does not exist: {file_path}", 0)
        return ""


def file_action(
    operation_func,
    source_path: Path,
    destination_path: Path,
    vlogger: VerbosityLogger = VerbosityLogger(),
    operation_name: str = "",
    overwrite: bool = False,
) -> None:
    source_path = Path(source_path)
    destination_path = Path(destination_path)

    try:
        if destination_path.exists() and overwrite:
            destination_path.unlink()
        operation_func(source_path, destination_path)
        vlogger.info(
            f"File {operation_name} {source_path} completed successfully to {destination_path}.",
            0,
        )
    except shutil.Error as e:
        vlogger.error(f"Failed to {operation_name} {source_path}: {e}", 0)


def copy_file(
    source_path: Path,
    destination_path: Path,
    vlogger: VerbosityLogger = VerbosityLogger(),
    overwrite: bool = False,
) -> None:
    file_action(
        shutil.copy2,
        source_path,
        destination_path,
        vlogger,
        operation_name="copied",
        overwrite=overwrite,
    )


def move_file(
    source_path: Path,
    destination_path: Path,
    vlogger: VerbosityLogger = VerbosityLogger(),
    overwrite: bool = False,
) -> None:
    file_action(
        shutil.move,
        source_path,
        destination_path,
        vlogger,
        operation_name="moved",
        overwrite=overwrite,
    )


def rename_files(
    source_directory: Path,
    target_extension: str,
    vlogger: VerbosityLogger = VerbosityLogger(),
):
    source_directory = Path(source_directory)
    for file_path in source_directory.iterdir():
        if file_path.suffix == target_extension:
            new_filename = dasherize(underscore(file_path.stem)) + target_extension
            new_file_path = source_directory / new_filename
            file_path.rename(new_file_path)
            vlogger.info(f"Renamed file: {file_path.name} -> {new_filename}", 1)


compression_functions = {
    "zstd": (zstandard.compress, zstandard.decompress, "zst"),
    "snappy": (snappy.compress, snappy.decompress, "snappy"),
    "gzip": (deflate.gzip_compress, deflate.gzip_decompress, "gz"),
    "lzo": (lzo.compress, lzo.decompress, "lzo"),
}


def compress_data(file_path: Path, compression_codec: str) -> None:
    file_path = Path(file_path)
    if compression_codec not in compression_functions:
        raise ValueError("Invalid compression codec")

    compress_func, _, _ = compression_functions[compression_codec]
    with open(file_path.with_suffix(".json"), "rb") as file:
        data = file.read()
        compressed_data = compress_func(data)

    compressed_file_path = file_path.with_suffix(
        f".json.{compression_functions[compression_codec][2]}"
    )
    with open(compressed_file_path, "wb") as file:
        file.write(compressed_data)


def decompress_data(file_path: Path, compression_codec: str) -> None:
    file_path = Path(file_path)
    if compression_codec not in compression_functions:
        raise ValueError("Invalid compression codec")

    _, decompress_func, _ = compression_functions[compression_codec]
    with open(file_path, "rb") as file:
        compressed_data = file.read()
        decompressed_data = decompress_func(compressed_data)

    decompressed_file_path = file_path
    with open(decompressed_file_path, "wb") as file:
        file.write(decompressed_data)


def get_compression_codec(
    file_path: Path, compression_codec: Optional[str] = None
) -> Optional[str]:
    if compression_codec is not None:
        return compression_codec

    file_extension = file_path.suffix[1:]
    for codec, (_, _, ext) in compression_functions.items():
        if ext == file_extension:
            return codec
    return None


def write_json(
    data: dict,
    file_path: Union[str, Path],
    compression_codec: Optional[str] = None,
    vlogger: VerbosityLogger = VerbosityLogger(),
) -> Path:
    file_path = Path(file_path)

    # If no compression_codec is provided, save the data as a regular JSON file
    if compression_codec is None:
        filename = file_path.with_suffix(".json")
        vlogger.info(f"[START] Write data to {filename}", 0)
        with open(filename, "w") as file:
            json.dump(data, file, default=str, indent=4)
        vlogger.info(f"[END] Write data to {filename}", 0)
        return filename

    # If a compression_codec is provided, compress and save the data with the specified codec
    elif compression_codec in compression_functions:
        compress_func, _, _ = compression_functions[compression_codec]
        compressed_data = compress_func(
            json.dumps(data, default=str, indent=4).encode()
        )
        filename = file_path.with_suffix(
            f".json.{compression_functions[compression_codec][2]}"
        )
        vlogger.info(f"[START] Write data to {filename}", 0)
        with open(filename, "wb") as file:
            file.write(compressed_data)
        vlogger.info(f"[END] Write data to {filename}", 0)
        return filename

    # If an invalid compression_codec is provided, raise an error
    else:
        raise ValueError("Invalid compression codec")


def generate_random_string(length):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )

def read_json(
    file_path: Union[str, Path],
    compression_codec: Optional[str] = None,
    vlogger: VerbosityLogger = VerbosityLogger(),
) -> dict:
    file_path = Path(file_path)
    compression_codec = get_compression_codec(file_path, compression_codec)

    if compression_codec is not None:
        random_suffix = generate_random_string(8)
        decompressed_filename = file_path.with_name(
            f"decompressed_{random_suffix}.json"
        )
        shutil.copy(file_path, decompressed_filename)
        decompress_data(decompressed_filename, compression_codec)
        delete_after_read = True
    else:
        decompressed_filename = file_path
        delete_after_read = False

    vlogger.info(f"Reading data from {decompressed_filename}", 0)
    with open(decompressed_filename, "r") as file:
        data = json.load(file)

    if delete_after_read:
        os.remove(decompressed_filename)  # Delete the decompressed file

    return data

