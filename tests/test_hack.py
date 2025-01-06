import json
from src.hack_metamask import decrypt_metamask_vault


import pytest


@pytest.mark.parametrize(
    "vault, password",
    [
        (
            '{"data":"0MByYgMFk6V4dYZC/N1SxxbMeWPXEtVktMlM4t2gIg0mblM4HGbawHggj4cvwsLRmtIM3nT6f8KcceGhDHJJGB1iWmpVeC4HhA+QR75MdbyR4fhZ9AyvDoSQ0K1m7ckziRWExQG0s9xj4x+0x3k45UDYziKMTXWgrD3SwkkP5asMOOITcdR0rdlmndAIcBz+IBf3zs76EEpsUJx6dhHqRUxAgfH4WRLRq/h2/LyhfnKvhmH+RYz6MZ/sa5P+fcCgZCtOTOdbu8LdJBHsXewUY43d2ti+QfrGmvXCP0ZHj97XWTWCdTwTuDIx/nXPXWhQzVXKVlKarQ5YvmauCWG3QJrYDa3sTduVMuFRwS/+1pIID+ybhrQft2EVRxBVkqcBu/gCCHeM7oOwTEw+UEv5GgduZ5iwFD/KMGRUlh9igoumtzsMIY6BOOQzQBbg5WREQA2Gbh4W+DEK6M2TxJeCg6BkVgT4QuXxgvJK7YFXNsEYNFh/LZ9FOosbx+TXiMJuJrr+czTmzA==","iv":"3/XB0MgtPNz8yFQ0GhkRZQ==","keyMetadata":{"algorithm":"PBKDF2","params":{"iterations":600000}},"salt":"jReEwKFNQ5y3hfwOSQtTALWcKtlB26y5Tu1mk7LkJA8="}',
            "12345678",
        )
    ],
)
def test_metamask_vault_decryption(vault, password):
    data = json.loads(vault)
    decrypted = decrypt_metamask_vault(data, password)
    found = any(
        d["data"]["mnemonic"]
        == "license recipe sunny wife pigeon again unfold car buyer pupil tortoise this"
        for d in decrypted
    )
    assert found, "Mnemonic phrase decryption failed"
    print(decrypted)


# decrypted_data = decrypt_metamask_vault(v, password)
# print(decrypted_data)  # 假设原始数据是utf-8编码的字符串
