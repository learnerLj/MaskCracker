import argparse
import logging
from pathlib import Path

from src.generate_dic import generate_dict
from src.hack_chrome_password import (beauty_print_chrome,
                                      hack_chrome_login_info)
from src.hack_metamask import (beauty_print_metamask, extract_metamask_vault,
                               hack_metamask)
from src.hashcat import generate_metamask_hash


def generate_dict_command(directory: Path, chrome_pass: bool) -> None:
    # Execute the generate-dict sub-command
    logging.info(
        f"Generating dictionary in {directory}, chrome passwords included: {chrome_pass}"
    )
    generate_dict(directory, chrome_pass)


def chrome_password_command() -> None:
    # Execute the chrome-password sub-command
    login_infos = hack_chrome_login_info()
    beauty_print_chrome(login_infos)


def decrypt_metamask_command(password: str) -> None:
    # Execute the decrypt-metamask sub-command
    decrypted_data = hack_metamask(password)
    beauty_print_metamask(decrypted_data)


def prepare_hashcat_command(hashfile: Path, dict_dir: Path) -> None:
    # Execute the prepare-hashcat sub-command
    logging.info(
        f"Preparing hashcat with hashfile: {hashfile}, dictionary directory: {dict_dir}"
    )

    vault = extract_metamask_vault()
    generate_metamask_hash(vault_dict=vault, hashfile_path=hashfile)

    repo_path = Path(__file__).resolve().parent.parent
    hashcat_repo_path = repo_path / "hashcat"
    dictionary_path = dict_dir / "plain_pass_*"

    # Linux or macOS
    bash_path = repo_path / "run_hashcat.sh"
    execute_path = hashcat_repo_path / "hashcat"
    bash_script = f"{execute_path} -m 26600 --self-test-disable {hashfile.resolve()} {dictionary_path.resolve()}\n"
    bash_path.write_text(bash_script)
    logging.info(f"Generated bash script at {bash_path}")

    # Windows
    bat_path = repo_path / "run_hashcat.bat"
    bat_script = (
        "@echo off\n"
        f'pushd "{hashcat_repo_path.resolve()}"\n'
        f"hashcat.exe -m 26600 --self-test-disable {hashfile.resolve()} {dictionary_path.resolve()}\n"
        "popd\n"
    )
    bat_path.write_text(bat_script)
    logging.info(f"Generated batch script at {bat_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test your Metamask's security if a hacker invades your computer"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # sub-command: generate-dict
    parser_generate = subparsers.add_parser("generate-dict", help="Generate dictionary")
    parser_generate.add_argument(
        "directory", type=str, help="Directory to generate dictionary"
    )
    parser_generate.add_argument(
        "--chrome-pass",
        action="store_true",
        help="Include Chrome passwords in dictionary",
    )

    # sub-command: chrome-password
    subparsers.add_parser("chrome-password", help="Print Chrome password")

    # sub-command: decrypt-metamask
    parser_metamask = subparsers.add_parser(
        "decrypt-metamask", help="Decrypt Metamask wallet"
    )
    parser_metamask.add_argument(
        "password", type=str, help="Password to decrypt Metamask wallet"
    )

    # sub-command: prepare-hashcat
    parser_hashcat = subparsers.add_parser(
        "prepare-hashcat", help="Generate hashfile and init dictionary directory"
    )
    parser_hashcat.add_argument("hashfile", type=str, help="Hash file path to write")
    parser_hashcat.add_argument("dict_dir", type=str, help="Dictionary directory path")

    args = parser.parse_args()

    try:
        if args.command == "generate-dict":
            generate_dict_command(
                directory=Path(args.directory), chrome_pass=args.chrome_pass
            )
        elif args.command == "chrome-password":
            chrome_password_command()
        elif args.command == "decrypt-metamask":
            decrypt_metamask_command(password=args.password)
        elif args.command == "prepare-hashcat":
            prepare_hashcat_command(
                hashfile=Path(args.hashfile), dict_dir=Path(args.dict_dir)
            )
        else:
            parser.print_help()
    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)


if __name__ == "__main__":
    main()
