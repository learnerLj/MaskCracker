import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from src.hack_chrome_password import hack_chrome_login_info
from src.utils import extract_file, get_files_in_dir, is_subpath, repo_path


def extract_files_in_directory(directory: Path, is_delete: bool = False):
    if not directory.is_dir():
        raise ValueError(f"Error: The path {directory} is not a valid directory.")

    supported_suffixes = [
        ".tar.gz",
        ".tgz",
        ".tar.bz2",
        ".tbz2",
        ".tar.xz",
        ".txz",
        ".tar",
        ".zip",
        ".gz",
    ]
    file_paths = get_files_in_dir(directory, suffix=supported_suffixes)

    with ThreadPoolExecutor() as executor:
        futures = []
        for p in file_paths:
            futures.append(executor.submit(extract_file, p, None, is_delete))

        for future in tqdm(
            as_completed(futures), total=len(futures), desc="Extracting files"
        ):
            try:
                future.result()
            except Exception as e:
                logging.error(f"An error occurred during task execution: {e}")

    logging.info("All compressed files have been processed")


def split_pass(dir: Path, is_delete: bool = False):
    """
    Traverse all .txt files in the directory, extract passwords, and save them to a new file.
    Display the progress of the process.
    :param dir: The path to the target folder
    :param is_delete: Whether to delete the original file, default is False
    """
    if not os.path.isdir(dir):
        logging.info(f"no directory for password splitting: {dir}")
        return

    # Ignore files starting with "plain_pass_" as these are flattened
    # Ignore files ending with "only_pass.txt" as these are the result of password separation
    txt_files = get_files_in_dir(
        dir, suffix=".txt", not_prefix="plain_pass_", not_suffix="only_pass.txt"
    )

    if not txt_files:
        logging.info("No txt files found for password splitting")
        return

    logging.info(f"Found {len(txt_files)} txt files that need password splitting")

    def split_line(line: str) -> str | None:
        line = line.strip()
        if not line:
            return None

        colon_pos = line.find(":")
        semicolon_pos = line.find(";")
        delimiter_pos = (
            min(colon_pos, semicolon_pos)
            if colon_pos != -1 and semicolon_pos != -1
            else max(colon_pos, semicolon_pos)
        )
        if delimiter_pos != -1:
            password = line[delimiter_pos + 1 :].strip()
        else:
            return None

        if len(password) < 8:
            return None
        return password

    def process_file(file_path: Path):
        # output_file = ".".join(file_path.split(".")[:-1]) + "_only_pass.txt"
        output_file = file_path.with_name(file_path.stem + "_only_pass.txt")
        with open(file_path, "r", encoding="utf-8", errors="replace") as infile, open(
            output_file, "w", encoding="utf-8"
        ) as outfile:
            for line in infile:
                password = split_line(line)
                if not password:
                    continue
                outfile.write(password + "\n")
        if is_delete:
            file_path.unlink()

    # Display progress using tqdm, with default concurrency of min(32, os.cpu_count() + 4), no manual control needed
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(process_file, file): file for file in txt_files}
        for future in tqdm(
            as_completed(futures),
            total=len(txt_files),
            desc="Password Separation Progress",
        ):
            file = futures[future]
            try:
                future.result()
            except Exception as e:
                logging.error(
                    f"Error occurred while separating passwords in file {file}: {e}"
                )

    logging.info("Password separation completed")


def chrome_pass_to_txt(dir: Path):
    login_infos = hack_chrome_login_info()
    passwords = [info.password + "\n" for info in login_infos]
    file_path = dir / "chrome_pass.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("".join(passwords), encoding="utf-8")


def flatten_pass(dir: Path, size: int = 512, is_delete: bool = False):
    """
    Recursively read all files ending with `only_pass.txt` in the directory and merge them into multiple files.
    :param dir: Target directory
    :param size: Maximum size of each merged file (in MB), default is 512MB
    """

    max_size = size * 1024 * 1024
    buffer = []
    output_file_index = 1
    buffer_size = 0

    # seen_pass = ScalableBloomFilter(initial_capacity=400_000_000, error_rate=error_rate)

    def write_lines_to_file():
        nonlocal output_file_index, buffer, buffer_size
        output_file_path = dir / f"plain_pass_{output_file_index}.txt"
        output_file_path.write_text("".join(buffer), encoding="utf-8")

        output_file_index += 1
        buffer = []
        buffer_size = 0
        logging.info(f"Write complete: {output_file_path}")

    # Check if the directory contains only plain_pass_*.txt files
    all_files = list(dir.iterdir())
    if all(
        f.name.startswith("plain_pass_") and f.name.endswith(".txt")
        for f in all_files
        if not f.name.startswith(".")
    ):
        logging.info("only plain_pass_*.txt files exist, skip flatten")
        return
    # Delete previously merged files
    files_delete = get_files_in_dir(dir, prefix="plain_pass_", suffix=".txt")
    for file in files_delete:
        os.remove(file)

    logging.info("Cleanup complete: All old plain_pass_*.txt files have been deleted")

    # Retrieve all files that need to be processed
    files_to_process = get_files_in_dir(dir, suffix="only_pass.txt")

    # If there are no files to process, exit directly
    if not files_to_process:
        logging.info("No files found that need flattening.")
        return

    logging.info(f"Found {len(files_to_process)} files that need flattening")

    # Use a progress bar to display the progress
    for file_path in tqdm(
        files_to_process,
        total=len(files_to_process),
        desc="Flattening progress",
        unit="file",
    ):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as infile:
            for line in infile:
                line = line.strip()
                if not line or len(line) < 8:
                    continue
                buffer.append(line + "\n")
                buffer_size += len(line) + 1

                if buffer_size >= max_size:
                    write_lines_to_file()
        if is_delete:
            os.remove(file_path)

    if buffer:
        write_lines_to_file()

    logging.info("Flattening completed")


def generate_dict(directory: Path, add_chrome_pass: bool = False):

    need_to_split = directory / "need_to_split"
    if not os.path.isdir(need_to_split):
        need_to_split = None

    if add_chrome_pass:
        chrome_pass_to_txt(directory)

    # First, extract all compressed files in the directory
    extract_files_in_directory(directory, is_delete=True)

    txt_files = get_files_in_dir(
        directory, suffix=".txt", not_prefix="plain_pass_", not_suffix="only_pass.txt"
    )

    # rename the txt files that do not need to split
    if need_to_split:
        txt_files = [file for file in txt_files if not is_subpath(file, need_to_split)]
    for file_name in txt_files:
        new_name = file_name.with_name(file_name.stem + "_only_pass.txt")
        file_name.rename(new_name)

    # Then process the files that need password separation
    if need_to_split:
        assert isinstance(need_to_split, Path)
        split_pass(need_to_split, is_delete=True)

    # Only process files ending with only_pass.txt
    flatten_pass(directory, is_delete=True)

    for entry in os.scandir(directory):
        if entry.is_dir():
            shutil.rmtree(entry.path)


if __name__ == "__main__":
    directory = repo_path / "output/dictionary"
    generate_dict(directory, add_chrome_pass=True)
