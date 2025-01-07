import gzip
import logging
import shutil
import tarfile
import zipfile
from pathlib import Path


def get_files_in_dir(
    directory: Path,
    prefix: str | list[str] = "",
    suffix: str | list[str] = "",
    not_prefix: str | list[str] = "",
    not_suffix: str | list[str] = "",
) -> list[Path]:

    # If the parameter is a string, convert it to a list for uniform processing
    if isinstance(prefix, str):
        prefix = [prefix] if prefix else []
    if isinstance(suffix, str):
        suffix = [suffix] if suffix else []
    if isinstance(not_prefix, str):
        not_prefix = [not_prefix] if not_prefix else []
    if isinstance(not_suffix, str):
        not_suffix = [not_suffix] if not_suffix else []

    files_to_process = []

    for file in directory.rglob("*"):
        if not file.is_file() or file.name.startswith(
            "."
        ):  # Skip non-files and hidden files
            continue

        if prefix and not any(file.name.startswith(p) for p in prefix):
            continue
        if not_prefix and any(file.name.startswith(p) for p in not_prefix):
            continue

        if suffix and not any(file.name.endswith(s) for s in suffix):
            continue
        if not_suffix and any(file.name.endswith(s) for s in not_suffix):
            continue

        files_to_process.append(file)
    return files_to_process


def extract_file(file_path: Path, output_dir: Path = None, is_delete: bool = False):
    """
    Extract a single file, supporting multiple compression formats.
    """

    output_dir = output_dir or file_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)
    file_name = file_path.name
    extract_target = output_dir / file_path.stem
    try:
        if extract_target.exists():
            logging.info(f"Skipping: {file_name} already extracted")
            return
        # .tar.gz, .tgz
        if file_path.suffixes[-2:] == [".tar", ".gz"] or file_path.suffix == ".tgz":
            with tarfile.open(file_path, "r:gz") as tar:
                tar.extractall(path=output_dir)
            logging.info(f"Decompressed: {file_name} -> {output_dir}")
        #  .tar.bz2, .tbz2
        elif file_path.suffixes[-2:] == [".tar", ".bz2"] or file_path.suffix == ".tbz2":
            with tarfile.open(file_path, "r:bz2") as tar:
                tar.extractall(path=output_dir)
            logging.info(f"Decompressed: {file_name} -> {output_dir}")
        # .tar.xz, .txz
        elif file_path.suffixes[-2:] == [".tar", ".xz"] or file_path.suffix == ".txz":
            with tarfile.open(file_path, "r:xz") as tar:
                tar.extractall(path=output_dir)
            logging.info(f"Decompressed: {file_name} -> {output_dir}")
        # .tar
        elif file_path.suffix == ".tar":
            with tarfile.open(file_path, "r:") as tar:
                tar.extractall(path=output_dir)
            logging.info(f"Decompressed: {file_name} -> {output_dir}")
        # .zip
        elif file_path.suffix == ".zip":
            with zipfile.ZipFile(file_path, "r") as zipf:
                zipf.extractall(path=output_dir)
            logging.info(f"Decompressed: {file_name} -> {output_dir}")
            # .gz (Single file GZip compression)
        elif file_path.suffix == ".gz":
            # The target file after decompression (removing the .gz extension)
            decompressed_file = output_dir / file_path.stem
            if decompressed_file.exists():
                logging.info(f"Skipping: {file_name} already decompressed")
                return
            # Use gzip to decompress the file
            with gzip.open(file_path, "rb") as gz_file, decompressed_file.open(
                "wb"
            ) as out_f:
                shutil.copyfileobj(gz_file, out_f)
            logging.info(f"Decompressed: {file_name} -> {decompressed_file}")

        else:  # Unsupported file format
            raise ValueError(f"Unsupported file type: {file_name}")

        if is_delete:
            file_path.unlink()  # Delete the file
            logging.info(f"Deleted: {file_name}")
    except Exception as e:

        logging.error(f"Error occurred while extracting {file_name}: {e}")
        raise RuntimeError(f"Failed to extract {file_name}: {e}")


def is_subpath(path: Path, directory: Path) -> bool:
    try:
        path_resolved = path.resolve()
        directory_resolved = directory.resolve()
        return directory_resolved in path_resolved.parents
    except ValueError:
        return False
