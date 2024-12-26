"""
Script to decrypt Chrome's stored passwords from Login Data databases.
This script is specifically for older Chrome versions that use AES-128-CBC encryption with a fixed IV.
"""

import os
import sys
import glob
import sqlite3
import hashlib
import subprocess
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad


def get_login_data_paths() -> list:
    """
    Locate Chrome's Login Data database files across different profiles.
    Paths include:
    - ~/Library/Application Support/Google/Chrome/Profile*/Login Data
    - ~/Library/Application Support/Google/Chrome/Default/Login Data
    Returns:
        A list of paths to Login Data database files.
    """
    # Search for Login Data files in Profile* directories
    paths = glob.glob(os.path.expanduser(
        "~/Library/Application Support/Google/Chrome/Profile*/Login Data"
    ))
    # If no Profile* directories, try the Default profile
    if not paths:
        default_path = os.path.expanduser(
            "~/Library/Application Support/Google/Chrome/Default/Login Data"
        )
        if os.path.exists(default_path):
            paths = [default_path]
    return paths


def fetch_safe_storage_key(service_name: str = "Chrome") -> str:
    """
    Retrieve the Chrome Safe Storage Key from the macOS Keychain.
    Args:
        service_name (str): The service name in Keychain (e.g., 'Chrome').
    Returns:
        The Safe Storage Key as a string.
    """
    try:
        # Use macOS 'security' CLI to fetch the password
        cmd = f"security find-generic-password -ga '{service_name}' 2>&1 | awk '/password:/ {{print $2}}'"
        raw_output = subprocess.check_output(cmd, shell=True, text=True).strip()
        return raw_output.replace('"', '')  # Remove surrounding quotes
    except subprocess.CalledProcessError:
        print(f"ERROR: Failed to retrieve {service_name} Safe Storage Key from Keychain.")
        sys.exit(1)


def chrome_decrypt(encrypted_value: bytes, key_16: bytes) -> str:
    """
    Decrypt an encrypted password using AES-128-CBC.
    Args:
        encrypted_value (bytes): The encrypted value from Chrome's database.
        key_16 (bytes): The 16-byte key derived from PBKDF2.
    Returns:
        The decrypted password as a string.
    """
    # Remove the 'v10' prefix
    enc_pass = encrypted_value[3:]
    # Chrome uses a fixed IV of 16 bytes filled with 0x20 (space)
    iv = b'\x20' * 16
    # Perform AES decryption
    try:
        cipher = AES.new(key_16, AES.MODE_CBC, iv)
        decrypted = unpad(cipher.decrypt(enc_pass), AES.block_size)
        return decrypted.decode('utf-8', errors='replace')
    except Exception as e:
        return f"[Decryption Error: {str(e)}]"


def process_login_data(login_data_path: str, safe_storage_key: str) -> list:
    """
    Process a single Login Data database to decrypt stored credentials.
    Args:
        login_data_path (str): Path to the Login Data database.
        safe_storage_key (str): Chrome Safe Storage Key from macOS Keychain.
    Returns:
        A list of tuples (url, username, decrypted_password).
    """
    # Derive the 16-byte key using PBKDF2
    key_16 = hashlib.pbkdf2_hmac(
        'sha1',
        safe_storage_key.encode('utf-8'),
        b'saltysalt',
        1003
    )[:16]

    decrypted_list = []
    # Create a temporary copy of the database to avoid file lock issues
    temp_login_data_path = f"{login_data_path}.temp"
    # shutil.copy2(login_data_path, temp_login_data_path)
    with open(login_data_path, 'rb') as src, open(temp_login_data_path, 'wb') as dst:
        dst.write(src.read())

    try:
        # Connect to the copied database
        conn = sqlite3.connect(temp_login_data_path)
        cursor = conn.cursor()

        # Query for stored credentials
        cursor.execute("SELECT username_value, password_value, origin_url FROM logins")
        for username, encrypted_password, url in cursor.fetchall():
            if not username or not encrypted_password:
                continue
            if not encrypted_password.startswith(b'v10'):
                continue  # Skip non-AES-CBC entries

            # Decrypt the password
            decrypted_password = chrome_decrypt(encrypted_password, key_16)
            decrypted_list.append((url or "[No URL]", username, decrypted_password))

        cursor.close()
        conn.close()
    except Exception as e:
        print(f"ERROR processing {login_data_path}: {e}")
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_login_data_path):
            os.remove(temp_login_data_path)

    return decrypted_list


def main():
    """
    Main function to locate, process, and decrypt Chrome Login Data files.
    """
    # Locate all potential Login Data files
    login_data_paths = get_login_data_paths()
    if not login_data_paths:
        print("ERROR: No Login Data files found.")
        sys.exit(1)

    # Retrieve the Safe Storage Key from macOS Keychain
    safe_storage_key = fetch_safe_storage_key("Chrome")
    if not safe_storage_key:
        print("ERROR: Safe Storage Key retrieval failed.")
        sys.exit(1)

    # Process each Login Data file
    for login_data_path in login_data_paths:
        print(f"\n=== Processing: {login_data_path} ===")
        try:
            decrypted_credentials = process_login_data(login_data_path, safe_storage_key)
            for i, (url, username, password) in enumerate(decrypted_credentials, start=1):
                print(f"[{i}] URL: {url}")
                print(f"    Username: {username}")
                print(f"    Password: {password}")
        except Exception as e:
            print(f"ERROR: Failed to process {login_data_path}: {e}")


if __name__ == "__main__":
    main()