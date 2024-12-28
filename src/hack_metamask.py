import glob
import os
import platform
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from base64 import b64decode
import json
import re
from termcolor import colored
import shutil
import tempfile


def decrypt_metamask_vault(vault_dict: dict, password: str) -> list[dict]:
    if (
        "data" not in vault_dict
        or "iv" not in vault_dict
        or "salt" not in vault_dict
        or "keyMetadata" not in vault_dict
        or "params" not in vault_dict["keyMetadata"]
        or "iterations" not in vault_dict["keyMetadata"]["params"]
    ):
        raise ValueError("Missing required fields")
    encrypted_data = b64decode(vault_dict["data"])
    iv = b64decode(vault_dict["iv"])
    salt = b64decode(vault_dict["salt"])
    key_metadata = vault_dict["keyMetadata"]
    iterations = key_metadata["params"]["iterations"]

    # 创建密钥
    key = PBKDF2(password, salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)

    # tag 与数据一起传递，且位于数据末尾的16字节
    tag = encrypted_data[-16:]
    encrypted_data = encrypted_data[:-16]

    # 解密数据
    cipher = AES.new(key, AES.MODE_GCM, iv)
    cipher.update(b"")  # associated_data 参数，如果有的话
    decrypted_data = cipher.decrypt_and_verify(encrypted_data, tag)

    decrypted_list = json.loads(decrypted_data)
    for item in decrypted_list:
        if "data" in item and "mnemonic" in item["data"]:
            # 将 ASCII 码值列表转换为字符，并组合成字符串
            mnemonic_str = "".join(chr(code) for code in item["data"]["mnemonic"])
            item["data"]["mnemonic"] = mnemonic_str

    return decrypted_list


def get_metamask_vault_path():
    paths = []
    if platform.system() == "Darwin":
        p = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"
        )
        paths = glob.glob(os.path.join(p, "[0-9]*.log"))
    elif platform.system() == "Windows":
        user_profile = os.environ.get("USERPROFILE")
        if user_profile:
            p = os.path.join(
                user_profile,
                "AppData\\Local\\Google\\Chrome\\User Data\\Default\\Local Extension Settings\\nkbihfbeogaeaoehlefnkodbefgpgknn",
            )
            paths.extend(glob.glob(os.path.join(p, "[0-9]*.log")))

    if len(paths) != 1:
        raise Exception("Multiple or no MetaMask vault paths found.")
    else:
        return paths[0]

def extract_vault(data: str):

    # 尝试 1: 尝试解析为 JSON
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        pass  # 如果不是有效 JSON，继续下一步

    # 尝试 2: Pre-v3 cleartext
    pre_v3_matches = re.search(r'{"wallet-seed":"([^"}]*)"}', data)
    if pre_v3_matches:
        mnemonic = pre_v3_matches.group(1).replace("\\n", "")
        vault_matches = re.search(r'"wallet":("{[ -~]*\\"version\\":2}")', data)
        vault = json.loads(json.loads(vault_matches.group(1))) if vault_matches else {}
        return {"data": {"mnemonic": mnemonic, **vault}}

    # 尝试 3: Chromium 000003.log 文件 (Linux)
    linux_matches = re.search(r'"KeyringController":\{"vault":"({[^{}]*})"', data)
    if linux_matches:
        vault_body = linux_matches.group(1)
        return json.loads(vault_body)

    # 尝试 4: Chromium 000006.log 文件 (MacOS)
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
                "keyMetadata": json.loads(vault_parts[3].replace("\\", ""))
            }
        except Exception:
            pass

    # 尝试 5: Chromium 000005.ldb 文件 (Windows)
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
        print("Found multiple vaults!", vaults)
    return vaults[0]


def beauty_print(data: list[dict]) -> None:
    print("=" * 50)
    print(colored("Metamask Wallet Information", "blue", attrs=["bold", "underline"]))
    print("=" * 50)

    for i, wallet in enumerate(data, start=1):
        print(colored(f"[{i}]", "yellow", attrs=["bold"]))
        for key, value in wallet.items():
            if key == 'mnemonic':
                # 高亮 'mnemonic' 字段的值
                print(f"  {key.capitalize()}: {colored(value, 'green', attrs=['bold'])}")  
            else:
                # 使用 json.dumps 格式化其他字段
                formatted_value = json.dumps(value, indent=4) if isinstance(value, (dict, list)) else str(value)
                print(f"  {key.capitalize()}: {colored(formatted_value, 'cyan')}")  
        print(colored("-" * 50, "magenta"))

    print(colored("End of List", "red", attrs=["bold", "underline"]))
    print("=" * 50)



def hack_metamask(password: str) -> list[dict]:
    p = get_metamask_vault_path()
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, os.path.basename(p))
    shutil.copy(p, temp_file_path)
    
    p = temp_file_path
    with open(p, "rb") as file:
        data = file.read().decode("utf-8", errors="ignore")
    vault = extract_vault(data)
    shutil.rmtree(temp_dir)
    d = decrypt_metamask_vault(vault, password)
    return d


if __name__ == "__main__":
    passwd = "12345678"
    result = hack_metamask(passwd)
    beauty_print(result)

    """
    vault example:
    {'data': '...iMJuJrr+czTmzA==', 'iv': '3/XB0MgtPNz8yFQ0GhkRZQ==',
    'keyMetadata': {'algorithm': 'PBKDF2', 'params': {...}}, 
    'salt': 'jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8='}
    """
