# MetaMask 钱包私钥加密机制与 Bot 脚本私钥管理最佳实践

## 一、MetaMask 的私钥加密保存机制

### 1.1 概述

MetaMask 采用了强大的加密机制来保护用户的私钥和助记词。通过分析 MetaMask 的实现代码，我们可以了解其核心安全机制。

### 1.2 加密算法组合

MetaMask 使用以下加密技术组合：

#### 1.2.1 密钥派生：PBKDF2-SHA256

- **算法**: PBKDF2 (Password-Based Key Derivation Function 2)
- **哈希函数**: SHA-256
- **迭代次数**: 600,000 次（从早期的 10,000 次大幅提升）
- **派生密钥长度**: 256 位（32 字节）

```python
# 密钥派生示例代码
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from base64 import b64decode

# MetaMask 从用户密码派生加密密钥
salt = b64decode(vault["salt"])
password = "用户设置的密码"  # 仅用于演示，实际应从安全渠道获取
iterations = 600000  # MetaMask 当前使用的迭代次数

# 派生出 32 字节的加密密钥
encryption_key = PBKDF2(
    password, 
    salt, 
    dkLen=32,           # 密钥长度
    count=iterations,   # 迭代次数
    hmac_hash_module=SHA256
)
```

**为什么迭代次数很重要？**
- 更高的迭代次数使暴力破解变得更加耗时
- 600,000 次迭代意味着每次密码尝试都需要进行 60 万次哈希计算
- 大大降低了破解速度（例如从 57,736 H/s 降到 968 H/s）

#### 1.2.2 数据加密：AES-GCM

- **算法**: AES (Advanced Encryption Standard)
- **模式**: GCM (Galois/Counter Mode)
- **密钥长度**: 256 位
- **认证标签**: 16 字节（128 位）

```python
from Crypto.Cipher import AES

# 解密过程示例
iv = b64decode(vault["iv"])              # 初始化向量
encrypted_data = b64decode(vault["data"])

# AES-GCM 会在加密数据末尾附加 16 字节的认证标签
tag = encrypted_data[-16:]               # 提取认证标签
ciphertext = encrypted_data[:-16]        # 提取密文

# 使用 AES-GCM 解密
cipher = AES.new(encryption_key, AES.MODE_GCM, iv)
plaintext = cipher.decrypt_and_verify(ciphertext, tag)
```

**AES-GCM 的优势：**
- **机密性**: 加密数据，防止未授权读取
- **完整性**: 通过认证标签检测任何篡改
- **认证性**: 确保数据来源可信
- **效率高**: 可以并行处理，适合大量数据

### 1.3 Vault 数据结构

MetaMask 将加密的钱包信息存储在一个称为 "vault" 的 JSON 结构中：

```json
{
    "data": "base64编码的加密数据...",
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

**各字段说明：**

- **data**: 使用 AES-GCM 加密的钱包数据（助记词、私钥等）+ 认证标签
- **iv**: 初始化向量，确保相同的明文在不同加密中产生不同的密文
- **salt**: 密码盐值，确保相同的密码在不同用户间派生出不同的密钥
- **keyMetadata**: 包含密钥派生算法的元数据，特别是迭代次数

### 1.4 完整的加密流程

```
用户密码 + Salt (随机生成)
        ↓
    PBKDF2-SHA256
    (600,000 次迭代)
        ↓
    256位加密密钥
        ↓
    AES-GCM 加密
    (使用随机 IV)
        ↓
钱包数据 (助记词/私钥) → 加密数据 + 认证标签
        ↓
    存储到本地
```

### 1.5 存储位置

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

其中 `nkbihfbeogaeaoehlefnkodbefgpgknn` 是 MetaMask 扩展的 ID。

---

## 二、对 Bot 脚本私钥管理的启发

通过分析 MetaMask 的加密机制，我们可以总结出以下私钥管理的最佳实践，适用于各种 bot 脚本和自动化应用。

### 2.1 核心安全原则

#### 原则 1: 永远不要硬编码私钥

**❌ 错误做法:**
```python
# 永远不要这样做！
PRIVATE_KEY = "0x1234567890abcdef..."
```

**✅ 正确做法:**
```python
import os
from dotenv import load_dotenv

# 从环境变量或加密的配置文件中读取
load_dotenv()
PRIVATE_KEY = os.getenv('BOT_PRIVATE_KEY')
```

#### 原则 2: 使用强加密保护私钥

借鉴 MetaMask 的做法，对存储的私钥进行加密：

```python
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Hash import SHA256
import base64
import json

def encrypt_private_key(private_key: str, password: str) -> dict:
    """
    使用类似 MetaMask 的方式加密私钥
    """
    # 生成随机盐值和 IV
    salt = get_random_bytes(32)
    iv = get_random_bytes(16)
    
    # 使用 PBKDF2 从密码派生密钥
    key = PBKDF2(
        password, 
        salt, 
        dkLen=32, 
        count=600000,  # 使用高迭代次数
        hmac_hash_module=SHA256
    )
    
    # 使用 AES-GCM 加密
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    ciphertext, tag = cipher.encrypt_and_digest(private_key.encode())
    
    # 返回加密后的数据结构
    return {
        'data': base64.b64encode(ciphertext + tag).decode(),
        'iv': base64.b64encode(iv).decode(),
        'salt': base64.b64encode(salt).decode(),
        'iterations': 600000
    }

def decrypt_private_key(encrypted_data: dict, password: str) -> str:
    """
    解密私钥
    """
    # 解码 base64
    salt = base64.b64decode(encrypted_data['salt'])
    iv = base64.b64decode(encrypted_data['iv'])
    data = base64.b64decode(encrypted_data['data'])
    
    # 分离密文和标签
    tag = data[-16:]
    ciphertext = data[:-16]
    
    # 派生密钥
    key = PBKDF2(
        password, 
        salt, 
        dkLen=32, 
        count=encrypted_data['iterations'],
        hmac_hash_module=SHA256
    )
    
    # 解密
    cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    plaintext = cipher.decrypt_and_verify(ciphertext, tag)
    
    return plaintext.decode()
```

### 2.2 私钥存储方案对比

| 方案 | 安全性 | 便利性 | 适用场景 |
|------|--------|--------|----------|
| 环境变量 | ⭐⭐ | ⭐⭐⭐⭐ | 开发环境、临时脚本 |
| 加密配置文件 | ⭐⭐⭐ | ⭐⭐⭐ | 小型生产环境 |
| 密钥管理服务 (AWS KMS, Azure Key Vault) | ⭐⭐⭐⭐⭐ | ⭐⭐ | 企业级生产环境 |
| 硬件安全模块 (HSM) | ⭐⭐⭐⭐⭐ | ⭐ | 高安全需求场景 |

### 2.3 推荐的私钥管理架构

#### 方案 A: 开发环境 (使用 .env 文件)

```bash
# .env 文件 (务必添加到 .gitignore)
BOT_PRIVATE_KEY=your_encrypted_private_key_here
ENCRYPTION_PASSWORD=your_strong_password
```

```python
# bot.py
import os
from dotenv import load_dotenv

load_dotenv()

# 获取加密的私钥
encrypted_key = os.getenv('BOT_PRIVATE_KEY')
password = os.getenv('ENCRYPTION_PASSWORD')

# 解密后使用
private_key = decrypt_private_key(encrypted_key, password)
```

**.gitignore:**
```
.env
*.key
config/secrets/
```

#### 方案 B: 生产环境 (使用 AWS KMS)

```python
import boto3
import base64
import os

def get_private_key_from_kms():
    """
    从 AWS KMS 获取并解密私钥
    """
    # 从环境变量获取区域配置
    kms_client = boto3.client('kms', region_name=os.getenv('AWS_REGION', 'us-east-1'))
    
    # 存储在 KMS 中的加密私钥
    encrypted_key = os.getenv('ENCRYPTED_PRIVATE_KEY')
    
    # 使用 KMS 解密
    response = kms_client.decrypt(
        CiphertextBlob=base64.b64decode(encrypted_key),
        KeyId=os.getenv('KMS_KEY_ID')  # 从环境变量获取 KMS 密钥 ID
    )
    
    return response['Plaintext'].decode()
```

#### 方案 C: 企业环境 (使用 HashiCorp Vault)

```python
import hvac

def get_private_key_from_vault():
    """
    从 HashiCorp Vault 获取私钥
    """
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.getenv('VAULT_TOKEN')
    
    # 从 Vault 读取私钥
    secret = client.secrets.kv.v2.read_secret_version(
        path='bot/ethereum/private-key'
    )
    
    return secret['data']['data']['key']
```

### 2.4 私钥轮换策略

定期轮换私钥可以降低长期暴露的风险：

```python
import schedule
import time

def rotate_private_key():
    """
    私钥轮换流程
    """
    # 1. 生成新的私钥对
    new_private_key = generate_new_key()
    
    # 2. 将资金转移到新地址
    transfer_assets(old_key, new_key)
    
    # 3. 更新配置中的私钥
    update_encrypted_config(new_private_key)
    
    # 4. 安全销毁旧私钥
    securely_delete(old_private_key)
    
    print("私钥轮换完成")

# 每 30 天轮换一次
schedule.every(30).days.do(rotate_private_key)
```

### 2.5 访问控制和审计

#### 实施最小权限原则

```python
import time

class KeyManager:
    """
    私钥管理器，实施访问控制
    注意：这是概念性示例，实际使用需要完整实现所有辅助函数
    """
    def __init__(self, audit_logger):
        self._private_key = None
        self._logger = audit_logger
        self._access_count = 0
        self._max_access = 1000  # 最大访问次数
    
    def get_key(self, requester: str) -> str:
        """
        获取私钥（带审计）
        """
        # 记录访问日志
        self._logger.log({
            'action': 'key_access',
            'requester': requester,
            'timestamp': time.time(),
            'ip': self._get_client_ip()  # 需要实现：获取客户端 IP
        })
        
        # 检查访问次数
        self._access_count += 1
        if self._access_count > self._max_access:
            raise RuntimeError("密钥访问次数超限，可能存在泄漏")
        
        return self._private_key
    
    def sign_transaction(self, tx_data: dict) -> str:
        """
        签名交易（不暴露私钥）
        """
        # 在内部使用私钥签名，不返回私钥本身
        signature = self._sign_with_key(self._private_key, tx_data)  # 需要实现：签名函数
        
        self._logger.log({
            'action': 'transaction_signed',
            'tx_hash': self._hash_transaction(tx_data),  # 需要实现：哈希函数
            'timestamp': time.time()
        })
        
        return signature
    
    def _get_client_ip(self) -> str:
        """获取客户端 IP（需要根据实际环境实现）"""
        import socket
        return socket.gethostbyname(socket.gethostname())
    
    def _sign_with_key(self, key: str, data: dict) -> str:
        """使用私钥签名（需要根据具体区块链实现）"""
        # 示例：以太坊签名可使用 web3.py
        raise NotImplementedError("需要实现具体的签名逻辑")
    
    def _hash_transaction(self, tx_data: dict) -> str:
        """计算交易哈希（需要根据具体区块链实现）"""
        import hashlib
        import json
        return hashlib.sha256(json.dumps(tx_data, sort_keys=True).encode()).hexdigest()
```

### 2.6 内存安全

私钥在内存中的安全同样重要：

```python
# 注意：Python 字符串是不可变的，无法完全从内存中擦除
# 最佳实践是使用 bytes 对象并尽快删除引用

def secure_handle_private_key():
    """
    安全处理私钥的示例
    """
    # 使用 bytes 而不是 str
    private_key_bytes = get_decrypted_key_as_bytes()
    
    try:
        # 使用私钥进行必要操作
        result = sign_transaction(private_key_bytes)
        return result
    finally:
        # 尝试覆盖内存（Python 中效果有限）
        if isinstance(private_key_bytes, bytearray):
            for i in range(len(private_key_bytes)):
                private_key_bytes[i] = 0
        
        # 删除引用，让垃圾回收器处理
        del private_key_bytes

# 更好的做法：使用上下文管理器
class SecureKey:
    """
    安全密钥上下文管理器
    """
    def __init__(self, key_bytes: bytearray):
        self.key = key_bytes
    
    def __enter__(self):
        return self.key
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # 清零内存
        for i in range(len(self.key)):
            self.key[i] = 0
        del self.key

# 使用示例
with SecureKey(get_key_as_bytearray()) as key:
    # 使用密钥
    sign_transaction(key)
# 离开作用域后自动清理
```

**重要提示**：
- Python 的内存管理机制使得完全擦除内存中的敏感数据很困难
- 字符串（str）是不可变的，无法直接修改
- 使用 `bytearray` 可以提供更好的控制
- 考虑使用专门的密钥管理库，如 `cryptography` 或硬件安全模块

### 2.7 错误处理和日志

```python
import logging

# 配置日志（不记录敏感信息）
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
    安全地记录交易信息（隐藏私钥）
    """
    # ❌ 不要这样做
    # logging.info(f"Signing with key: {private_key}")
    
    # ✅ 正确做法
    logging.info(f"Transaction signed: {tx.hash}")
    logging.info(f"From address: {tx.from_address}")
    logging.info(f"To address: {tx.to_address}")
```

### 2.8 安全检查清单

在部署 bot 脚本前，请确保：

- [ ] 私钥从未在代码中硬编码
- [ ] 私钥文件已添加到 .gitignore
- [ ] 使用强加密算法（AES-256-GCM）保护存储的私钥
- [ ] 密钥派生使用足够的迭代次数（≥100,000）
- [ ] 实施了访问审计日志
- [ ] 配置了私钥轮换策略
- [ ] 错误日志不包含敏感信息
- [ ] 使用后及时清除内存中的私钥
- [ ] 生产环境使用密钥管理服务（KMS/Vault）
- [ ] 限制私钥的访问权限（文件权限 600）
- [ ] 启用多因素认证（MFA）保护密钥管理系统

---

## 三、总结

### 3.1 MetaMask 的关键安全措施

1. **强密钥派生**: PBKDF2-SHA256 + 600,000 迭代
2. **认证加密**: AES-GCM 同时提供机密性和完整性
3. **随机化**: 使用随机 salt 和 IV，确保每次加密结果不同
4. **元数据存储**: 保存算法参数，支持未来升级

### 3.2 Bot 脚本私钥管理的黄金法则

1. **永不明文存储**: 始终加密私钥
2. **分层防御**: 结合多种安全机制
3. **最小暴露**: 只在必要时访问私钥
4. **定期轮换**: 降低长期暴露风险
5. **审计追踪**: 记录所有关键操作
6. **安全删除**: 使用完毕立即清除

### 3.3 推荐阅读

- [OWASP 密钥管理备忘单](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html)
- [NIST 密钥管理指南](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-57pt1r5.pdf)
- [AWS 密钥管理最佳实践](https://docs.aws.amazon.com/kms/latest/developerguide/best-practices.html)

---

> **免责声明**: 本文档仅用于教育和安全研究目的。私钥管理涉及真实资产安全，请在生产环境中咨询专业安全人员。
