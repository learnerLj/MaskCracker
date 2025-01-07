import logging
from pathlib import Path

from hack_metamask import check_vault_fileds

logging.basicConfig(
    format="%(levelname)s - %(filename)s:%(lineno)d - %(message)s", level=logging.INFO
)


def generate_metamask_hash(vault_dict: dict, hashfile_path: Path) -> str:
    try:
        check_vault_fileds(vault_dict)

        salt = vault_dict["salt"]
        iv = vault_dict["iv"]
        data = vault_dict["data"]
        iterations = vault_dict["keyMetadata"]["params"]["iterations"]

        hash_string = f"$metamask${salt}${iterations}${iv}${data}"
        logging.info("Generated hash string successfully.")

        hashfile_path.parent.mkdir(parents=True, exist_ok=True)
        hashfile_path.write_text(hash_string)
        logging.info(f"Hash saved to: {hashfile_path}")
        return hash_string
    except KeyError as e:
        logging.error(f"Missing required key in vault_dict: {e}")
        raise ValueError(f"Vault dictionary missing key: {e}")

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        raise RuntimeError(f"Failed to generate metamask hash: {e}")


# 示例用法
if __name__ == "__main__":
    # 模拟 Metamask Vault 数据
    vault_example = {
        "data": "l4UkKy22JQqCpKVqMPI99fHAyekOMgjw2lsCcA6a0oy9UHn0kXczWuqZ/aw809INGF9Ib1k/bYZQU0wtIEST/9cucpMaU7RYbp2CnjB4KzQrMU0tiK8oneVMJKBQdRL7An8S9huUq3Mu3MA1hyD7Nhi1WIIDpBPSlRa9q7waYA1m3IFKi7SgoeNeqy8GA3QeEJdimN0VgD+CCYyvHltPYqQ9BxY9cgMY+cD3FWrMe2vddBV/ylNYOXjYwaKtQWhRPwkkMj3/TR5jW2wKb3VGX8aH+M6dxO5iAsRWdKrNVg+bPQ9+8k4FUDWcmefBySd9zIyrVTsfrRYGfaPRSkUBcEOOFPpnWZdLlamuOr3MwPSjOKUi6XIzVCoO71AWM3lSntIJKOf50/2ybhlX2DKpIb0HBc6Rf+eAI0bALZ2mnq/ATviRb6aKongmk6chlbnmZdroE5ylze3TgAl1F+GleVwuL76XWacj6ft2HyVAkzkJFTn+LY7+9TinImAPXElZ67wOJn12ip03ZQOWgfehwIhcs9wVPo07e73lHvEVIE1sPuxcZqNMzc5WzR6elhCSEavv4UzCVYpJfB+nbcLvF4nME85Gls9nRSMItDRlkDrGR5dbJuJMENLpEvMgirDPYffbnKrFz7r4p7J0kchmanCWhIVnegIRGu6IDIzBjkbtZ7WfksH3TV5Q0G0rEQ==",
        "iv": "3M/kKrGbjM/I00+RjQ9KUw==",
        "salt": "jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8=",
        "keyMetadata": {"algorithm": "PBKDF2", "params": {"iterations": 600000}},
    }

    current_dir = Path(__file__).resolve().parent
    hashfile_path = current_dir / "../dictionary/metamask_hash.txt"
    word_dict = current_dir / "../dictionary/rockyou.txt"
    generate_metamask_hash(vault_example, hashfile_path)
