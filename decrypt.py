import glob
import os
import platform
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Hash import SHA256
from base64 import b64decode
import json
import re


def decrypt_metamask_vault(vault_dict:dict, password:str)->dict:
    if ('data' not in vault_dict or
        'iv' not in vault_dict or
        'salt' not in vault_dict or
        'keyMetadata' not in vault_dict or
        'params' not in vault_dict['keyMetadata'] or
        'iterations' not in vault_dict['keyMetadata']['params']):
        raise ValueError("Missing required fields")
    encrypted_data = b64decode(vault_dict['data'])
    iv = b64decode(vault_dict['iv'])
    salt = b64decode(vault_dict['salt'])
    key_metadata = vault_dict['keyMetadata']
    iterations = key_metadata['params']['iterations']
    
    # 创建密钥
    key = PBKDF2(password, salt, dkLen=32, count=iterations, hmac_hash_module=SHA256)
    
    # tag 与数据一起传递，且位于数据末尾的16字节
    tag = encrypted_data[-16:]
    encrypted_data = encrypted_data[:-16]
    
    # 解密数据
    cipher = AES.new(key, AES.MODE_GCM, iv)
    cipher.update(b"")  # associated_data 参数，如果有的话
    decrypted_data = cipher.decrypt_and_verify(encrypted_data, tag)

    decrypted_dict = json.loads(decrypted_data)
    for item in decrypted_dict:
        if 'data' in item and 'mnemonic' in item['data']:
            # 将 ASCII 码值列表转换为字符，并组合成字符串
            mnemonic_str = ''.join(chr(code) for code in item['data']['mnemonic'])
            item['data']['mnemonic'] = mnemonic_str
    
    return decrypted_dict

def get_metamask_vault_paths():
    paths = []
    if platform.system() == "Darwin": 
        p = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn")
        paths = glob.glob(os.path.join(p, "[0-9]*.log"))
    elif platform.system() == "Windows":
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            p = os.path.join(user_profile, "AppData\\Local\\Google\\Chrome\\User Data\\Default\\Local Extension Settings\\nkbihfbeogaeaoehlefnkodbefgpgknn")
            paths.extend(glob.glob(os.path.join(p, "[0-9]*.log")))
        
        
    return paths
    

def extract_vault_from_file(file_path :str):
    with open(file_path, 'rb') as file:
        data = file.read()
        data = data.decode('utf-8', errors='ignore')
    try:
        # 尝试1: 直接解析 JSON
        j = json.loads(data)
        return j
    except Exception:
        pass  # 如果不是有效的 JSON，继续尝试其他方法

    # 尝试2: pre-v3 cleartext
    matches = re.search(r'{"wallet-seed":"([^"}]*)"}', data)
    if matches:
        mnemonic = matches.group(1).replace('\\n', '')
        vault_matches = re.search(r'"wallet":("{[ -~]*\\"version\\":2}")', data)
        vault = json.loads(json.loads(vault_matches.group(1))) if vault_matches else {}
        return {
            "data": {
                "mnemonic": mnemonic,
                **vault
            }
        }

    # 尝试3: chromium 000003.log file on linux
    pattern = r'"KeyringController":\{"vault":"(\\?.*?)"}'
    matches = re.search(pattern, data)
    if matches:
        vault_body = matches.group(0)[29:].replace('\\', "").strip('"')
        return json.loads(vault_body)

    # 尝试4: chromium 000006.log on MacOS
    matches = re.search(r'KeyringController":(\{"vault":".*?=\\""\})', data)
    if matches:
        keyring_controller_state_fragment = matches.group(1)
        data_regex = r'\\"data\\":\\"([A-Za-z0-9+/]*=*)'
        iv_regex = r',\\"iv\\":\\"([A-Za-z0-9+/]{10,40}=*)'
        salt_regex = r',\\"salt\\":\\"([A-Za-z0-9+/]{10,100}=*)\\"'
        key_meta_regex = r',\\"keyMetadata\\":(.*}})'

        vault_parts = [re.search(regex, keyring_controller_state_fragment).group(1) for regex in [data_regex, iv_regex, salt_regex, key_meta_regex]]
        return {
            "data": vault_parts[0],
            "iv": vault_parts[1],
            "salt": vault_parts[2],
            "keyMetadata": json.loads(vault_parts[3].replace('\\', ''))
        }

    # 尝试5: chromium 000005.ldb on windows
    match_regex = r'Keyring[0-9][^\}]*({[^\{\}]*\\"\})'
    capture_regex = r'Keyring[0-9][^\}]*({[^\{\}]*\\"\})'
    iv_regex = r'\\"iv.{1,4}[^A-Za-z0-9+/]{1,10}([A-Za-z0-9+/]{10,40}=*)'
    data_regex = r'\\"[^":,is]*\\":\\"([A-Za-z0-9+/]*=*)'
    salt_regex = r',\\"salt.{1,4}[^A-Za-z0-9+/]{1,10}([A-Za-z0-9+/]{10,100}=*)'
    vaults = []
    for match in re.finditer(match_regex, data):
        s = re.search(capture_regex, match.group(0)).group(1)
        d, i, s = [re.search(r, s).group(1) for r in [data_regex, iv_regex, salt_regex]]
        if d and i and s:
            vaults.append({"data": d, "iv": i, "salt": s})

    if not vaults:
        raise Exception("No vaults found.")
    if len(vaults) > 1:
        print('Found multiple vaults!', vaults)
    return vaults[0]

if __name__ == "__main__":
    ps = get_metamask_vault_paths()
    for p in ps:
        vault = extract_vault_from_file(p)
        d = decrypt_metamask_vault(vault,"12345678")
        print(d)



    """
    {'data': '...iMJuJrr+czTmzA==', 'iv': '3/XB0MgtPNz8yFQ0GhkRZQ==',
    'keyMetadata': {'algorithm': 'PBKDF2', 'params': {...}}, 
    'salt': 'jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8='}
    
    """

# v = "{\"data\":\"0MByYgMFk6V4dYZC/N1SxxbMeWPXEtVktMlM4t2gIg0mblM4HGbawHggj4cvwsLRmtIM3nT6f8KcceGhDHJJGB1iWmpVeC4HhA+QR75MdbyR4fhZ9AyvDoSQ0K1m7ckziRWExQG0s9xj4x+0x3k45UDYziKMTXWgrD3SwkkP5asMOOITcdR0rdlmndAIcBz+IBf3zs76EEpsUJx6dhHqRUxAgfH4WRLRq/h2/LyhfnKvhmH+RYz6MZ/sa5P+fcCgZCtOTOdbu8LdJBHsXewUY43d2ti+QfrGmvXCP0ZHj97XWTWCdTwTuDIx/nXPXWhQzVXKVlKarQ5YvmauCWG3QJrYDa3sTduVMuFRwS/+1pIID+ybhrQft2EVRxBVkqcBu/gCCHeM7oOwTEw+UEv5GgduZ5iwFD/KMGRUlh9igoumtzsMIY6BOOQzQBbg5WREQA2Gbh4W+DEK6M2TxJeCg6BkVgT4QuXxgvJK7YFXNsEYNFh/LZ9FOosbx+TXiMJuJrr+czTmzA==\",\"iv\":\"3/XB0MgtPNz8yFQ0GhkRZQ==\",\"keyMetadata\":{\"algorithm\":\"PBKDF2\",\"params\":{\"iterations\":600000}},\"salt\":\"jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8=\"}"
# password = "12345678"  # 替换为你的密码

# decrypted_data = decrypt_metamask_vault(v, password)
# print(decrypted_data)  # 假设原始数据是utf-8编码的字符串