# MetaMask Private Key Encryption Mechanism and Best Practices for Bot Script Key Management

## I. MetaMask's Private Key Encryption Mechanism

### 1.1 Overview

MetaMask employs a robust encryption mechanism to protect users' private keys and seed phrases. By analyzing MetaMask's implementation, we can understand its core security mechanisms.

### 1.2 Encryption Algorithm Combination

MetaMask uses the following combination of cryptographic techniques:

#### 1.2.1 Key Derivation: PBKDF2-SHA256

- **Algorithm**: PBKDF2 (Password-Based Key Derivation Function 2)
- **Hash Function**: SHA-256
- **Iterations**: 600,000 (significantly increased from 10,000)
- **Derived Key Length**: 256 bits (32 bytes)

```python
# Key derivation example code
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from base64 import b64decode

# MetaMask derives encryption key from user password
salt = b64decode(vault["salt"])
password = "user_password"  # For demonstration only, should be obtained securely
iterations = 600000  # Current iteration count used by MetaMask

# Derive 32-byte encryption key
encryption_key = PBKDF2(
    password, 
    salt, 
    dkLen=32,           # Key length
    count=iterations,   # Iteration count
    hmac_hash_module=SHA256
)
```

**Why is the iteration count important?**
- Higher iteration counts make brute-force attacks more time-consuming
- 600,000 iterations means each password attempt requires 600,000 hash calculations
- Significantly reduces cracking speed (e.g., from 57,736 H/s to 968 H/s)

#### 1.2.2 Data Encryption: AES-GCM

- **Algorithm**: AES (Advanced Encryption Standard)
- **Mode**: GCM (Galois/Counter Mode)
- **Key Length**: 256 bits
- **Authentication Tag**: 16 bytes (128 bits)

```python
from Crypto.Cipher import AES

# Decryption process example
iv = b64decode(vault["iv"])              # Initialization Vector
encrypted_data = b64decode(vault["data"])

# AES-GCM appends a 16-byte authentication tag to the encrypted data
tag = encrypted_data[-16:]               # Extract authentication tag
ciphertext = encrypted_data[:-16]        # Extract ciphertext

# Decrypt using AES-GCM
cipher = AES.new(encryption_key, AES.MODE_GCM, iv)
plaintext = cipher.decrypt_and_verify(ciphertext, tag)
```

**Advantages of AES-GCM:**
- **Confidentiality**: Encrypts data to prevent unauthorized access
- **Integrity**: Detects any tampering through authentication tag
- **Authentication**: Ensures data comes from a trusted source
- **Efficiency**: Can be parallelized, suitable for large amounts of data

### 1.3 Vault Data Structure

MetaMask stores encrypted wallet information in a JSON structure called a "vault":

```json
{
    "data": "base64-encoded encrypted data...",
    "iv": "3/XB0MgtPNz8yFQ0GhkRZQ==",
    "salt": "jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8=",
    "keyMetadata": {
        "algorithm": "PBKDF2",
        "params": {
            "iterations": 600000
        }
    }
}
```

**Field Descriptions:**

- **data**: Wallet data (seed phrase, private keys, etc.) encrypted with AES-GCM + authentication tag
- **iv**: Initialization vector, ensures the same plaintext produces different ciphertext in different encryptions
- **salt**: Password salt, ensures the same password derives different keys for different users
- **keyMetadata**: Contains metadata about the key derivation algorithm, particularly the iteration count

### 1.4 Complete Encryption Flow

```
User Password + Salt (randomly generated)
        ↓
    PBKDF2-SHA256
    (600,000 iterations)
        ↓
    256-bit Encryption Key
        ↓
    AES-GCM Encryption
    (using random IV)
        ↓
Wallet Data (seed phrase/private keys) → Encrypted Data + Auth Tag
        ↓
    Store Locally
```

### 1.5 Storage Location

**macOS:**
```
~/Library/Application Support/Google/Chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn/
```

**Windows:**
```
%USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default\Local Extension Settings\nkbihfbeogaeaoehlefnkodbefgpgknn\
```

**Linux:**
```
~/.config/google-chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn/
```

Where `nkbihfbeogaeaoehlefnkodbefgpgknn` is the MetaMask extension ID.

---

## II. Insights for Bot Script Private Key Management

By analyzing MetaMask's encryption mechanism, we can derive the following best practices for private key management, applicable to various bot scripts and automated applications.

### 2.1 Core Security Principles

#### Principle 1: Never Hardcode Private Keys

**❌ Wrong Approach:**
```python
# Never do this!
PRIVATE_KEY = "0x1234567890abcdef..."
```

**✅ Correct Approach:**
```python
import os
from dotenv import load_dotenv

# Read from environment variables or encrypted config files
load_dotenv()
PRIVATE_KEY = os.getenv('BOT_PRIVATE_KEY')
```

#### Principle 2: Use Strong Encryption to Protect Private Keys

Following MetaMask's approach, encrypt stored private keys:

```python
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256
import base64
import json

def encrypt_private_key(private_key: str, password: str) -> dict:
    """
    Encrypt private key using MetaMask-like method
    """
    # Generate random salt and IV
    salt = get_random_bytes(32)
    iv = get_random_bytes(16)
    
    # Derive key from password using PBKDF2
    key = PBKDF2(
        password, 
        salt, 
        dkLen=32, 
        count=600000,  # Use high iteration count
        hmac_hash_module=SHA256
    )
    
    # Encrypt using AES-GCM
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(private_key.encode())
    
    # Return encrypted data structure
    return {
        'data': base64.b64encode(ciphertext + tag).decode(),
        'iv': base64.b64encode(iv).decode(),
        'salt': base64.b64encode(salt).decode(),
        'iterations': 600000
    }

def decrypt_private_key(encrypted_data: dict, password: str) -> str:
    """
    Decrypt private key
    """
    # Decode base64
    salt = base64.b64decode(encrypted_data['salt'])
    iv = base64.b64decode(encrypted_data['iv'])
    data = base64.b64decode(encrypted_data['data'])
    
    # Separate ciphertext and tag
    tag = data[-16:]
    ciphertext = data[:-16]
    
    # Derive key
    key = PBKDF2(
        password, 
        salt, 
        dkLen=32, 
        count=encrypted_data['iterations'],
        hmac_hash_module=SHA256
    )
    
    # Decrypt
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    
    return plaintext.decode()
```

### 2.2 Private Key Storage Solutions Comparison

| Solution | Security | Convenience | Use Case |
|----------|----------|-------------|----------|
| Environment Variables | ⭐⭐ | ⭐⭐⭐⭐ | Development, temporary scripts |
| Encrypted Config Files | ⭐⭐⭐ | ⭐⭐⭐ | Small production environments |
| Key Management Service (AWS KMS, Azure Key Vault) | ⭐⭐⭐⭐⭐ | ⭐⭐ | Enterprise production |
| Hardware Security Module (HSM) | ⭐⭐⭐⭐⭐ | ⭐ | High-security requirements |

### 2.3 Recommended Private Key Management Architecture

#### Solution A: Development Environment (using .env files)

```bash
# .env file (must be added to .gitignore)
BOT_PRIVATE_KEY=your_encrypted_private_key_here
ENCRYPTION_PASSWORD=your_strong_password
```

```python
# bot.py
import os
from dotenv import load_dotenv

load_dotenv()

# Get encrypted private key
encrypted_key = os.getenv('BOT_PRIVATE_KEY')
password = os.getenv('ENCRYPTION_PASSWORD')

# Decrypt and use
private_key = decrypt_private_key(encrypted_key, password)
```

**.gitignore:**
```
.env
*.key
config/secrets/
```

#### Solution B: Production Environment (using AWS KMS)

```python
import boto3
import base64
import os

def get_private_key_from_kms():
    """
    Retrieve and decrypt private key from AWS KMS
    """
    # Get region configuration from environment variable
    kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    
    # Encrypted private key stored in KMS
    encrypted_key = os.getenv('ENCRYPTED_PRIVATE_KEY')
    
    # Decrypt using KMS
    response = kms_client.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_key),
        KeyId=os.getenv('KMS_KEY_ID')  # Get KMS key ID from environment variable
    )
    
    return response['Plaintext'].decode()
```

#### Solution C: Enterprise Environment (using HashiCorp Vault)

```python
import hvac

def get_private_key_from_vault():
    """
    Retrieve private key from HashiCorp Vault
    """
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.getenv('VAULT_TOKEN')
    
    # Read private key from Vault
    secret = client.secrets.kv.v2.read_secret_version(
        path='bot/ethereum/private-key'
    )
    
    return secret['data']['data']['key']
```

### 2.4 Key Rotation Strategy

Regular key rotation reduces long-term exposure risk:

```python
import schedule
import time

def rotate_private_key():
    """
    Private key rotation process
    """
    # 1. Generate new key pair
    new_private_key = generate_new_key()
    
    # 2. Transfer assets to new address
    transfer_assets(old_key, new_key)
    
    # 3. Update private key in configuration
    update_encrypted_config(new_private_key)
    
    # 4. Securely destroy old private key
    securely_delete(old_private_key)
    
    print("Key rotation completed")

# Rotate every 30 days
schedule.every(30).days.do(rotate_private_key)
```

### 2.5 Access Control and Auditing

#### Implement Principle of Least Privilege

```python
class KeyManager:
    """
    Key manager implementing access control
    """
    def __init__(self, audit_logger):
        self._private_key = None
        self._logger = audit_logger
        self._access_count = 0
        self._max_access = 1000  # Maximum access count
    
    def get_key(self, requester: str) -> str:
        """
        Get private key (with auditing)
        """
        # Log access
        self._logger.log({
            'action': 'key_access',
            'requester': requester,
            'timestamp': time.time(),
            'ip': get_client_ip()
        })
        
        # Check access count
        self._access_count += 1
        if self._access_count > self._max_access:
            raise SecurityError("Key access limit exceeded, possible leak")
        
        return self._private_key
    
    def sign_transaction(self, tx_data: dict) -> str:
        """
        Sign transaction (without exposing private key)
        """
        # Use private key internally for signing, don't return the key itself
        signature = sign_with_key(self._private_key, tx_data)
        
        self._logger.log({
            'action': 'transaction_signed',
            'tx_hash': hash_transaction(tx_data),
            'timestamp': time.time()
        })
        
        return signature
```

### 2.6 Memory Security

Security of private keys in memory is equally important:

```python
import ctypes
import sys

def secure_delete_from_memory(variable):
    """
    Securely delete sensitive data from memory
    """
    # Overwrite memory
    if isinstance(variable, str):
        buffer = ctypes.create_string_buffer(len(variable))
        ctypes.memset(ctypes.addressof(buffer), 0, len(variable))
    
    # Delete reference
    del variable

# Usage example
private_key = get_decrypted_key()
# ... use private key ...
# Delete immediately after use
secure_delete_from_memory(private_key)
```

### 2.7 Error Handling and Logging

```python
import logging

# Configure logging (without sensitive information)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

def safe_log_transaction(tx):
    """
    Safely log transaction information (hiding private key)
    """
    # ❌ Don't do this
    # logging.info(f"Signing with key: {private_key}")
    
    # ✅ Correct approach
    logging.info(f"Transaction signed: {tx.hash}")
    logging.info(f"From address: {tx.from_address}")
    logging.info(f"To address: {tx.to_address}")
```

### 2.8 Security Checklist

Before deploying bot scripts, ensure:

- [ ] Private keys are never hardcoded in the code
- [ ] Private key files are added to .gitignore
- [ ] Strong encryption (AES-256-GCM) is used to protect stored private keys
- [ ] Key derivation uses sufficient iterations (≥100,000)
- [ ] Access audit logging is implemented
- [ ] Key rotation strategy is configured
- [ ] Error logs don't contain sensitive information
- [ ] Private keys are cleared from memory after use
- [ ] Key management service (KMS/Vault) is used in production
- [ ] Access permissions to private keys are restricted (file permissions 600)
- [ ] Multi-factor authentication (MFA) is enabled for key management systems

---

## III. Summary

### 3.1 MetaMask's Key Security Measures

1. **Strong Key Derivation**: PBKDF2-SHA256 + 600,000 iterations
2. **Authenticated Encryption**: AES-GCM provides both confidentiality and integrity
3. **Randomization**: Uses random salt and IV to ensure different encryption results each time
4. **Metadata Storage**: Saves algorithm parameters to support future upgrades

### 3.2 Golden Rules for Bot Script Private Key Management

1. **Never Store in Plaintext**: Always encrypt private keys
2. **Defense in Depth**: Combine multiple security mechanisms
3. **Minimal Exposure**: Only access private keys when necessary
4. **Regular Rotation**: Reduce long-term exposure risk
5. **Audit Trail**: Log all critical operations
6. **Secure Deletion**: Clear immediately after use

### 3.3 Recommended Reading

- [OWASP Key Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)
- [NIST Key Management Guidelines](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)
- [AWS Key Management Best Practices](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)

---

> **Disclaimer**: This document is for educational and security research purposes only. Private key management involves real asset security. Please consult professional security personnel in production environments.
