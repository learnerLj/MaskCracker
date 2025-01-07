<div align="center">
<img src="logo.png" alt="hack-browser-data logo" width="440px" />
</div>



# MaskCracker: Is Your Metamask Wallet Safe?

MaskCracker is a testing tool used to assess whether your Metamask wallet remains secure in the following scenarios:
1. If all website passwords stored in your browser are leaked, is your wallet still safe?
2. If you accidentally run malicious code, can your wallet be cracked?

## How It Works

MaskCracker can:

- Export passwords from the Chrome browser.
- Use large language models or deep learning to infer password structures and generate the most probable password dictionary.
- Combine these dictionaries with the world's fastest password-cracking tool, [Hashcat](https://hashcat.net/hashcat), to crack the Metamask mnemonic or private key.

> **Disclaimer**: This tool is intended for security research only. Any legal or related liability arising from the use of this tool shall be borne solely by the user. The original author does not assume any legal responsibility.

---

## Installation

### 1. Install Python dependencies

This project uses Poetry for dependency management. Please refer to the [official documentation](https://python-poetry.org/docs/) for installation instructions.

Then install the dependencies:

```bash
poetry install
```

### 2. About Hashcat

> If you only want to print Chrome passwords and decrypt Metamask using your password, you can skip installing Hashcat.

- **Download the fixed version of Hashcat**: The official Hashcat Metamask module is outdated. We recommend using the fixed version provided in this project. You can download the compiled `hashcat-fix-metamask.tar.gz` (which includes `hashcat` for macOS and `hashcat.exe` for Windows) from [learnerLj/hashcat](https://github.com/learnerLj/hashcat/releases/tag/fix-version). You can also refer to `BUILD*.md` to compile it yourself.

- **Extract it into the repository’s root directory**.

- **Verify the installation**:
  - macOS: Run `./hashcat/hashcat -b` to benchmark.
  - Windows: Navigate to the `hashcat` folder and run `hashcat.exe -b`. If you see driver errors, please update your graphics drivers.

---

## Usage

> **MacOS Users**: Using the `security` command to retrieve passwords from Keychain may be monitored by security controls. **Do not** run this on a work computer.

Activate the virtual environment:

```bash
poetry shell
python src/main.py
```

Set the `PYTHONPATH` environment variable to point to the project root, then choose one of the following methods:

```bash
# For macOS and Linux
export PYTHONPATH=$PWD

# For Windows CMD
set PYTHONPATH=%cd%

# For Windows PowerShell
$env:PYTHONPATH=$PWD
```

### Common Usage

```bash
# Print all Chrome passwords
python src/main.py chrome-password

# Decrypt Metamask mnemonic and private key using a password
python src/main.py decrypt-metamask 12345678
```

> **Note**: After printing sensitive information, please clear the terminal (`clear`) to avoid leaks.

---

## Cracking Passwords

### 1. Generate a Dictionary

⚠️ **Important**: The original dictionary files will be processed. Make sure to back them up before proceeding.

Run the following commands from the repository root. It automatically extracts compressed files in the `dictionary` folder.

```bash
# --chrome-pass is optional. If added, it uses the exported Chrome passwords to generate a dictionary.
python src/main.py generate-dict --chrome-pass output/dictionary
```

Within the `dictionary` folder, there is a `need_to_split` subfolder. Passwords there are in a format like `username:password`, `username;password`, `hash:password`, or `hash;password`, and need to be split. This helps utilize existing rainbow tables or leaked password databases.

Place any other plaintext password lists directly under the `dictionary` folder (outside the `need_to_split` subfolder). After processing, all valid Metamask-like passwords are filtered out.

Example structure:

```
dictionary
├── crackstation-human-only.txt.gz
├── need_to_split
│   └── 68_linkedin_found_hash_plain.txt.zip
└── rockyou.txt.zip

dictionary
├── plain_pass_1.txt
├── plain_pass_2.txt
└── plain_pass_3.txt
```

> Each `plain_pass` file can be up to 512MB.  
> Even with bloom filters, resource usage can be large, so duplicates won’t be removed automatically. Consider using Redis or other databases if you need deduplication.

### 2. Generate Hashcat Target File and Run Scripts

```bash
python src/main.py prepare-hashcat output/hashcat-target.txt output/dictionary
```

This generates a Hashcat target file in the format `$metamask${salt}${iterations}${iv}${cypher}` used by Hashcat for cracking. It also takes the dictionary folder as the second parameter. Afterward, `run_hashcat.sh` (for macOS/Linux) and `run_hashcat.bat` (for Windows) are created in the project root to run Hashcat.

### 3. Run Hashcat

```bash
# On macOS
bash run_hashcat.sh

# On Windows
.\run_hashcat.bat
```

Hashcat will keep running. You can press `s` to check the status or `q` to quit:

```
[s]tatus [p]ause [b]ypass [c]heckpoint [f]inish [q]uit =>
```

- **Status**: `Running` means it’s still attempting passwords, `Exhausted` means it has tried all possibilities, and `Cracked` means it found a valid password.
- **Time.Estimated**: Estimated time to completion.
- **Guess.Base**: The current dictionary file in use.
- **Speed.#2**: Current speed (number of passwords tested per second).
- **Progress**: How many passwords have been attempted so far.

If a password is found, the status shows `Cracked`, and you’ll see output like `sH3TV5Q0G0rEQ==:12345678`, indicating `12345678` is the correct password.

> To learn more about creating secure passwords, check out [Presentation](https://gist.github.com/leplatrem/b1f23563a3028c66276ddf48705fac84).

---

## Password Dictionaries

> 1–3 have already been included in my [Hashcat Release](https://github.com/learnerLj/hashcat/releases/tag/fix-version) as `dictionary.zip`. Just extract it into `output`.

1. [RockYou](https://github.com/josuamarcelc/common-password-list/blob/main/rockyou.txt/rockyou.txt.zip)  
   No need to split. Originates from the 2009 RockYou breach, leaking ~32M passwords.
2. [LinkedIn password](https://github.com/brannondorsey/PassGAN/releases/download/data/68_linkedin_found_hash_plain.txt.zip)  
   Requires splitting. Originates from the 2012 LinkedIn data breach, containing ~160M hashed passwords.
3. [CrackStation](https://crackstation.net/crackstation-wordlist-password-cracking-dictionary.htm)  
   Choose the file with only passwords (no splitting needed).
4. [Collection #1](https://github.com/p4wnsolo/breach-torrents)  
   Requires splitting. After extraction, you’ll get a folder named `Collection #1` containing multiple `.tar.gz` files.  
   `magnet:?xt=urn:btih:b39c603c7e18db8262067c5926e7d5ea5d20e12e&dn=Collection+1`.
5. Collection #2–#5  
   After extraction, you’ll get `Collection 2-5 & Antipublic`, containing multiple `.tar.gz` files.  
   `magnet:?xt=urn:btih:d136b1adde531f38311fbf43fb96fc26df1a34cd&dn=Collection+%232-%235+%26+Antipublic`.

**Not Tested Yet:**

6. [BreachCompilation](https://github.com/p4wnsolo/breach-torrents)  
   Released by an anonymous user on Torrents in 2017, containing data from various known breaches (LinkedIn, MySpace, Adobe, Dropbox, etc.).  
   `magnet:?xt=urn:btih:7ffbcd8cee06aba2ce6561688cf68ce2addca0a3&dn=BreachCompilation&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80...`  
   `magnet:?xt=urn:btih:7FFBCD8CEE06ABA2CE6561688CF68CE2ADDCA0A3&dn=BreachCompilation`

> All the above dictionaries come from publicly available sources and are intended for research purposes only.


## Principle Explanation

Blog post in progress...

## TODO

- [ ] Decrypt Metamask `.ldb` so that mnemonic can be retrieved in any case.
- [ ] Use rules to generate additional possible passwords from the user’s known passwords.
- [ ] Use large language models or deep learning to infer Chrome passwords and generate a custom dictionary.


## FAQ

### `No module named 'src'`

Make sure you have activated the virtual environment with `poetry shell` and you are running commands from the project root (not from another directory). Also ensure `PYTHONPATH` points to the project root.

### Missing dependencies

Errors like `ModuleNotFoundError: No module named 'xxx'` can often be resolved by re-running `poetry install` and entering the virtual environment again with `poetry shell`.

### Unable to find Metamask vault

MaskCracker decrypts the Metamask log from Chrome’s local storage rather than fully encrypted `.ldb` data. If the wallet hasn’t been opened for a long time, the corresponding log may be deleted.

**Solution**: Reopen the Metamask extension page so that logs are generated again.

### Cracking speed too slow

Metamask’s PBKDF2-SHA256 iteration count increased from 10,000 to 600,000, which significantly slows down the cracking process.

On a MacBook M4 Pro (14+16), the speed dropped from ~57,736 H/s to ~968 H/s. The difference between Metal and OpenCL APIs is minimal.  
A 4060 GPU currently hits around ~2,400 H/s.

> Personal blog: [blog-blockchain.xyz](https://blog-blockchain.xyz/) for more fun and interesting blockchain tech articles.