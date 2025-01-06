import argparse
import os
from pathlib import Path
from src.generate_dic import (
    chrome_pass_to_txt,
    extract_files_in_directory,
    generate_dict,
    split_pass,
    flatten_pass,
)
from src.hack_chrome_password import hack_chrome_login_info, beauty_print_chrome
from src.hack_metamask import (
    beauty_print_metamask,
    extract_metamask_vault,
    hack_metamask,
)
from src.hashcat import generate_metamask_hash


def main():
    parser = argparse.ArgumentParser(
        description="test your metamask's security if hacker invade your computer"
    )
    subparsers = parser.add_subparsers(dest="command", help="sub-command help")

    # sub-command: generate-dict
    parser_generate = subparsers.add_parser("generate-dict", help="generate dictionary")
    parser_generate.add_argument(
        "directory", type=str, help="directory to generate dictionary"
    )
    parser_generate.add_argument(
        "--chrome-pass",
        action="store_true",
        help="include chrome passwords in dictionary",
    )

    # sub-command: chrome-password
    parser_chrome = subparsers.add_parser(
        "chrome-password", help="print chrome password"
    )

    # sub-command: decrypt-metamask
    parser_metamask = subparsers.add_parser(
        "decrypt-metamask", help="decrypt metamask wallet"
    )
    parser_metamask.add_argument(
        "password", type=str, help="password to decrypt metamask wallet"
    )

    # sub-command: hashfile
    parser_hashcat = subparsers.add_parser(
        "prepare-hashcat", help="generate hashfile and init dictionary directory"
    )
    parser_hashcat.add_argument("hashfile", type=str, help="hash file path to write")
    parser_hashcat.add_argument("dict_dir", type=str, help="dictionary directory path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
    elif args.command == "generate-dict":
        directory = args.directory
        add_chrome_pass = args.chrome_pass
        generate_dict(directory, add_chrome_pass)
    elif args.command == "chrome-password":
        login_infos = hack_chrome_login_info()
        beauty_print_chrome(login_infos)
    elif args.command == "decrypt-metamask":
        decrypted_data = hack_metamask(args.password)
        beauty_print_metamask(decrypted_data)
    elif args.command == "prepare-hashcat":
        hashfile_path = Path(args.hashfile)
        dict_dir = Path(args.dict_dir)

        dictionarys_path = dict_dir / "plain_pass_*"
        vault = extract_metamask_vault()
        generate_metamask_hash(vault_dict=vault, hashfile_path=hashfile_path)
        repo_path = Path(__file__).parent.parent
        hashcat_repo_path = repo_path / "hashcat"

        # linux or mac
        bash_path = repo_path / "run_hashcat.sh"
        exexute_path = hashcat_repo_path / "hashcat"
        with open(bash_path, "w") as bash_file:
            bash_file.write(
                f"{exexute_path} -m 26600 --self-test-disable {hashfile_path.resolve()} {dictionarys_path.resolve()}\n"
            )

        # windows
        bat_path = repo_path / "run_hashcat.bat"

        with open(bat_path, "w") as bat_file:
            bat_file.write("@echo off\n")
            bat_file.write(f'pushd "{hashcat_repo_path}"\n')
            bat_file.write(
                f"hashcat.exe -m 26600 --self-test-disable {hashfile_path.resolve()} {dictionarys_path.resolve()}\n"
            )
            bat_file.write("popd\n")


if __name__ == "__main__":
    main()
