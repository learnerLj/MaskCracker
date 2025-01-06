import argparse
import os
from src.generate_dic import (
    chrome_pass_to_txt,
    extract_files_in_directory,
    generate_dict,
    split_pass,
    flatten_pass,
)
from src.hack_chrome_password import hack_chrome_login_info, beauty_print_chrome
from src.hack_metamask import beauty_print_metamask, hack_metamask


def main():
    parser = argparse.ArgumentParser(
        description="test your metamask's security if hacker invade your computer"
    )
    subparsers = parser.add_subparsers(dest="command", help="sub-command help")

    # 子命令：generate-dict
    parser_generate = subparsers.add_parser("generate-dict", help="generate dictionary")
    parser_generate.add_argument(
        "directory", type=str, help="directory to generate dictionary"
    )
    parser_generate.add_argument(
        "--chrome-pass",
        action="store_true",
        help="include chrome passwords in dictionary",
    )

    # 子命令：chrome-password
    parser_chrome = subparsers.add_parser(
        "chrome-password", help="print chrome password"
    )

    # 子命令：decrypt-metamask
    parser_metamask = subparsers.add_parser(
        "decrypt-metamask", help="decrypt metamask wallet"
    )
    parser_metamask.add_argument(
        "password", type=str, help="password to decrypt metamask wallet"
    )

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


if __name__ == "__main__":
    main()
