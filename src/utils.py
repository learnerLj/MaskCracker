import gzip
import os
import shutil
import tarfile
import zipfile


def get_files_in_dir(
    directory: str,
    prefix: str | list[str] = "",
    suffix: str | list[str] = "",
    not_prefix: str | list[str] = "",
    not_suffix: str | list[str] = "",
) -> list[str]:

    # 如果参数是字符串，转换为列表，便于统一处理
    if isinstance(prefix, str):
        prefix = [prefix] if prefix else []
    if isinstance(suffix, str):
        suffix = [suffix] if suffix else []
    if isinstance(not_prefix, str):
        not_prefix = [not_prefix] if not_prefix else []
    if isinstance(not_suffix, str):
        not_suffix = [not_suffix] if not_suffix else []

    files_to_process = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.startswith("."):  # 跳过隐藏文件
                continue

            # 检查前缀条件
            if prefix and not any(file.startswith(p) for p in prefix):
                continue
            if not_prefix and any(file.startswith(p) for p in not_prefix):
                continue

            # 检查后缀条件
            if suffix and not any(file.endswith(s) for s in suffix):
                continue
            if not_suffix and any(file.endswith(s) for s in not_suffix):
                continue

            files_to_process.append(os.path.join(root, file))
    return files_to_process


def extract_file(file_path: str, output_dir=None, is_delete=False):
    """
    解压单个文件，支持多种压缩格式。
    """
    if output_dir is None:
        output_dir = os.path.dirname(file_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_name = os.path.basename(file_path)
    extracted_dir = os.path.splitext(os.path.splitext(file_name)[0])[
        0
    ]  # 去掉多层扩展名

    try:
        # 检查是否已经解压
        extract_target = os.path.join(output_dir, extracted_dir)
        if os.path.exists(extract_target):
            print(f"Skipping: {file_name} already extracted")
            return

        if file_path.endswith(".tar.gz") or file_path.endswith(".tgz"):
            # 处理 .tar.gz 文件
            with tarfile.open(file_path, "r:gz") as tar:
                tar.extractall(path=output_dir)
            print(f"decompressed: {file_name} -> {output_dir}")
        elif file_path.endswith(".tar.bz2") or file_path.endswith(".tbz2"):
            # 处理 .tar.bz2 文件
            with tarfile.open(file_path, "r:bz2") as tar:
                tar.extractall(path=output_dir)
            print(f"decompressed: {file_name} -> {output_dir}")

        elif file_path.endswith(".tar.xz") or file_path.endswith(".txz"):
            # 处理 .tar.xz 文件
            with tarfile.open(file_path, "r:xz") as tar:
                tar.extractall(path=output_dir)
            print(f"decompressed: {file_name} -> {output_dir}")

        elif file_path.endswith(".tar"):
            # 处理 .tar 文件
            with tarfile.open(file_path, "r:") as tar:
                tar.extractall(path=output_dir)
            print(f"decompressed: {file_name} -> {output_dir}")

        elif file_path.endswith(".zip"):
            # 处理 .zip 文件
            with zipfile.ZipFile(file_path, "r") as zipf:
                zipf.extractall(path=output_dir)
            print(f"decompressed: {file_name} -> {output_dir}")

        elif file_path.endswith(".gz"):
            # 处理单个 .gz 文件（非 tar.gz）
            decompressed_file = os.path.join(output_dir, os.path.splitext(file_name)[0])
            if os.path.exists(decompressed_file):
                print(f"Skipping: {file_name} already decompressed")
                return
            with gzip.open(file_path, "rb") as gz_file:
                with open(decompressed_file, "wb") as out_f:
                    shutil.copyfileobj(gz_file, out_f)
            print(f"decompressed: {file_name} -> {decompressed_file}")

        else:
            raise ValueError(f"Not supported file type: {file_name}")

        # 如果需要删除源文件
        if is_delete:
            os.remove(file_path)
            print(f"Deleted: {file_name}")

    except Exception as e:
        raise RuntimeError(f"Error occurred while extracting {file_name}: {str(e)}")


def is_subpath(path, directory):
    path = os.path.abspath(path)
    directory = os.path.abspath(directory)

    relative_path = os.path.relpath(path, directory)

    # not in a parent directory of the given directory.
    # not just in the given directory itself
    return not relative_path.startswith(os.pardir) and relative_path != os.curdir
