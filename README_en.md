<div align="center">
<img src="logo.png" alt="hack-browser-data logo" width="440px" />
</div>

**A Python script to decrypt passwords stored in Chrome’s Login Data database, compatible with macOS and Windows.**
This script extracts the encrypted `uri`, `username`, and `password` from Chrome’s local SQLite database and simulates Chrome’s encryption algorithm to decrypt the passwords using Python.

### **Features**

- **`get_login_data_paths`:** Locates the Chrome login data database files in different user profiles.

- `safe_storage_key`:

  Retrieves the stored key.

  - On Windows: Uses DPAPI (Data Protection API) to decrypt the key.
  - On macOS: Retrieves the Chrome security storage key from the macOS Keychain and derives the key using Python, based on Chrome's source code.

- `chrome_decrypt`:

  Decrypts the stored passwords in the Chrome login database.

  - On Windows: Uses AES-128-GCM with the IV extracted from the encrypted data.
  - On macOS: Uses AES-128-CBC with a fixed 16-byte IV (`b"\x20"`) and decrypts the password from the cipher text.

### **Installation**

This project uses **Poetry** for dependency management. Ensure Poetry is installed by following the [installation guide](https://python-poetry.org/docs/). Then, run:

```bash
poetry install
```

### **Usage**

Run directly with Poetry:

```bash
poetry run python main.py
```

Alternatively, activate the virtual environment and run:

```bash
poetry shell
python main.py
```

### **Disclaimer**

This tool is intended for security research purposes only. The user assumes full responsibility for any legal consequences that may arise from the use of this tool. The author is not liable for any damages or legal issues resulting from its usage.

> blog：http://blog-blockchain.xyz/
