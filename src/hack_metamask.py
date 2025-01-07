import glob
import json
import platform
import re
import shutil
import tempfile
from base64 import b64decode
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import PBKDF2
from termcolor import colored


def get_metamask_vault_path() -> Path:
    if platform.system() == "Darwin":
        base_path = (
            Path.home()
            / "Library/Application Support/Google/Chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"
        )
    elif platform.system() == "Windows":
        user_profile = Path.home()
        base_path = (
            user_profile
            / "AppData/Local/Google/Chrome/User Data/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"
        )
    else:
        raise EnvironmentError("Unsupported OS for locating MetaMask vault.")

    vault_files = glob.glob(str(base_path / "[0-9]*.log"))
    if len(vault_files) != 1:
        raise FileNotFoundError("Multiple or no MetaMask vault paths found.")
    return Path(vault_files[0])


def parse_vault_data(data: str):

    # Attempt 1: Try parsing as JSON
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        pass

    # Attempt 2: Pre-v3 cleartext
    pre_v3_matches = re.search(r'{"wallet-seed":"([^"}]*)"}', data)
    if pre_v3_matches:
        mnemonic = pre_v3_matches.group(1).replace("\\n", "")
        vault_matches = re.search(r'"wallet":("{[ -~]*\\"version\\":2}")', data)
        vault = json.loads(json.loads(vault_matches.group(1))) if vault_matches else {}
        return {"data": {"mnemonic": mnemonic, **vault}}

    # Attempt 3: Chromium 000003.log file (Linux)
    linux_matches = re.search(r'"KeyringController":\{"vault":"({[^{}]*})"', data)
    if linux_matches:
        vault_body = linux_matches.group(1)
        return json.loads(vault_body)

    # Attempt 4: Chromium 000006.log file (MacOS)
    macos_matches = re.search(r'KeyringController":(\{"vault":".*?=\\"\}"\})', data)
    if macos_matches:
        keyring_fragment = macos_matches.group(1)
        try:
            data_regex = r'\\"data\\":\\"([A-Za-z0-9+/]*=*)'
            iv_regex = r',\\"iv\\":\\"([A-Za-z0-9+/]{10,40}=*)'
            salt_regex = r',\\"salt\\":\\"([A-Za-z0-9+/]{10,100}=*)\\"'
            key_meta_regex = r',\\"keyMetadata\\":(.*}})'

            vault_parts = [
                re.search(regex, keyring_fragment).group(1)
                for regex in [data_regex, iv_regex, salt_regex, key_meta_regex]
            ]

            return {
                "data": vault_parts[0],
                "iv": vault_parts[1],
                "salt": vault_parts[2],
                "keyMetadata": json.loads(vault_parts[3].replace("\\", "")),
            }
        except Exception:
            pass

    # Attempt 5: Chromium 000005.ldb file (Windows)
    windows_matches = re.finditer(r'Keyring[0-9][^\}]*({[^\{\}]*\\"\})', data)
    vaults = []
    for match in windows_matches:
        capture = match.group(1)
        data_regex = r'\\"[^":,is]*\\":\\"([A-Za-z0-9+/]*=*)'
        iv_regex = r'\\"iv.{1,4}[^A-Za-z0-9+/]{1,10}([A-Za-z0-9+/]{10,40}=*)'
        salt_regex = r',\\"salt.{1,4}[^A-Za-z0-9+/]{1,10}([A-Za-z0-9+/]{10,100}=*)'

        try:
            d, i, s = [
                re.search(r, capture).group(1)
                for r in [data_regex, iv_regex, salt_regex]
            ]
            vaults.append({"data": d, "iv": i, "salt": s})
        except AttributeError:
            continue

    if not vaults:
        raise Exception("No vaults found or metamask is closed")
    if len(vaults) > 1:
        raise Exception("Found multiple vaults!", vaults)
    return vaults[0]


def check_vault_fileds(vault: dict) -> tuple[bytes, bytes, bytes, int]:
    required_keys = ["data", "iv", "salt", "keyMetadata"]
    for key in required_keys:
        if key not in vault:
            raise KeyError(f"Missing required field: {key}")

    encrypted_data = b64decode(vault["data"])
    iv = b64decode(vault["iv"])
    salt = b64decode(vault["salt"])
    iterations = vault["keyMetadata"]["params"]["iterations"]

    return encrypted_data, iv, salt, iterations


def decrypt_metamask_vault(vault_dict: dict, password: str) -> list[dict]:
    encrypted_data, iv, salt, iterations = check_vault_fileds(vault_dict)

    key = PBKDF2(password, salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)

    # The tag is passed along with the data and is the last 16 bytes of the data
    tag = encrypted_data[-16:]
    encrypted_data = encrypted_data[:-16]

    cipher = AES.new(key, AES.MODE_GCM, iv)
    try:
        decrypted_data = cipher.decrypt_and_verify(encrypted_data, tag)
    except Exception as e:
        raise (f"Decryption failed: {str(e)}")

    decrypted_list = json.loads(decrypted_data)
    for item in decrypted_list:
        if "data" in item and "mnemonic" in item["data"]:
            # Convert ASCII code list to characters and combine into a string
            mnemonic_str = "".join(chr(code) for code in item["data"]["mnemonic"])
            item["data"]["mnemonic"] = mnemonic_str

    return decrypted_list


def extract_metamask_vault() -> dict:
    vault_path = get_metamask_vault_path()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / vault_path.name
        shutil.copy(vault_path, temp_file)
        data = temp_file.read_text(encoding="utf-8", errors="ignore")

    return parse_vault_data(data)


def hack_metamask(password: str) -> list[dict]:
    vault = extract_metamask_vault()
    d = decrypt_metamask_vault(vault, password)
    return d


def beauty_print_metamask(data: list[dict]) -> None:
    print("=" * 50)
    print(colored("Metamask Wallet Information", "blue", attrs=["bold", "underline"]))
    print("=" * 50)

    for i, wallet in enumerate(data, start=1):
        print(colored(f"[{i}]", "yellow", attrs=["bold"]))
        for key, value in wallet.items():
            if key == "mnemonic":
                # Highlight the value of the 'mnemonic' field
                print(
                    f"  {key.capitalize()}: {colored(value, 'green', attrs=['bold'])}"
                )
            else:
                # Format other fields
                formatted_value = (
                    json.dumps(value, indent=4)
                    if isinstance(value, (dict, list))
                    else str(value)
                )
                print(f"  {key.capitalize()}: {colored(formatted_value, 'cyan')}")
        print(colored("-" * 50, "magenta"))

    print(colored("End of List", "red", attrs=["bold", "underline"]))
    print("=" * 50)


if __name__ == "__main__":
    passwd = "12345678"
    result = hack_metamask(passwd)
    beauty_print_metamask(result)

    """
    vault example:
    {'data': '...iMJuJrr+czTmzA==', 'iv': '3/XB0MgtPNz8yFQ0GhkRZQ==',
    'keyMetadata': {'algorithm': 'PBKDF2', 'params': {...}}, 
    'salt': 'jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8='}
    """
