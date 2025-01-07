<div align="center">
<img src="logo.png" alt="hack-browser-data logo" width="440px" />
</div>
<p align="left">
  <a href="./README_en.md">English Version Here</a> 
</p>

# MaskCracker：你的 Metamask 钱包安全吗？
MaskCracker 是一款测试工具，用于评估在以下场景下你的 Metamask 钱包是否安全：
1.	当浏览器中所有网站密码泄露时，你的钱包是否依然安全？
2.	当你不慎运行了恶意代码，钱包是否会被破解？

工作原理：
MaskCracker 可以：
- 导出 Chrome 浏览器中的密码。
- 使用大模型或深度学习推测密码结构，生成最有可能的密码字典。
- 结合密码库和世界最快的密码破解工具 [Hashcat](https://hashcat.net/hashcat)，破解 Metamask 的助记词或私钥。

> 免责声明：本工具仅用于安全研究，因使用本工具而产生的一切法律及相关责任由用户自行承担，原作者不承担任何法律责任。


## 安装

**1. 安装 python 依赖**

该项目使用 Poetry 进行依赖管理，可参考[安装教程](https://python-poetry.org/docs/)。
随后安装依赖：

```bash
poetry install
```

**2. 关于 Hashcat 的说明**

> 如果只想使用打印 chrome 密码和使用密码解密metamask功能，可以不安装 hashcat。

- 下载修复版本hashcat。由于官方 Hashcat 的 Metamask 模块已过时，建议使用本项目提供的修复版本。读者可以在 [learnerLj/hashcat](https://github.com/learnerLj/hashcat/releases/tag/fix-version) 中下载编译好的 `hashcat-fix-metamask.tar.gz`，其中包含 macos 的 `hashcat` 和 Windows 的 `hashcat.exe`。读者也可参考 `BUILD*.md` 自行编译。

- 解压到仓库根目录。

- 验证安装。
  - macOS: `./hashcat/hashcat -b` 进行 benchmark。
  - Windows: 进入 hashcat 目录，运行 hashcat.exe -b。如果出现驱动报错，请更新显卡驱动。


## 使用方法

> 🚨 MacOS 用户注意，通过 security 命令从 Keychain 获取密码可能被安全监控。*不要*再工作电脑上运行。

进入虚拟环境

```bash
$ poetry shell # 进入虚拟环境
$ python src/main.py

positional arguments:
  {generate-dict,chrome-password,decrypt-metamask,prepare-hashcat}
                        Available sub-commands
    generate-dict       Generate dictionary
    chrome-password     Print Chrome password
    decrypt-metamask    Decrypt Metamask wallet
    prepare-hashcat     Generate hashfile and init dictionary directory

options:
  -h, --help            show this help message and exit
```

设置环境变量 `PYTHONPATH`，指向项目根目录，选择一个运行。
```shell
# 对于 macOS 和 Linux
export PYTHONPATH=$PWD

# 对于 Windows CMD
set PYTHONPATH=%cd%

# 对于 Windows PowerShell
$env:PYTHONPATH=$PWD
```

### 常见用法
  
```bash 
# 打印chrome所有密码
python src/main.py chrome-password

# 使用密码解密 metamask 助记词和私钥
python src/main.py decrypt-metamask 12345678

```
> 🚨 打印敏感信息后请及时 `clear` 终端，避免泄露。

### 破解密码

**1. 生成字典**：

⚠️ 注意：原始字典文件将被处理，请务必保留原始密码字典备份。

密码库中 1-3 已经放在我的 [hashcat Release](https://github.com/learnerLj/hashcat/releases/tag/fix-version) 中，可以直接下载 `dictionary.zip`，解压到output下。

以下命令都建议在仓库根目录下运行。会自动解压字典文件夹下的压缩文件。
```bash
# --chrome-pass 可省略，若添加表示额外使用chrome密码生成字典，密码文件下载见下文密码库
python src/main.py generate-dict --chrome-pass output/dictionary
```

字典文件夹下的 `need_to_split` 文件夹，它下面的所有密码都是需要拆分的，格式类似`用户名:密码`、 `用户名;密码`、 `hash:密码`、`hash;密码`。这有助于使用已有的彩虹表或者泄漏的密码库。

其余明文密码直接放在 `dictionary` 下除了 `need_to_split` 下的任何其他位置即可。下面表示处理后的变化，会过滤出密码库中所有符合metamask的密码。

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
> 每个plain_pass最大512MB。
> 考虑到密码去重复即使用布隆过滤器，资源占用也很大，所以不会自动去重复。可以使用redis等数据库进行去重复。

**2. 生成 Hashcat 目标文件及运行脚本**

```bash
python src/main.py prepare-hashcat output/hashcat-target.txt output/dictionary
```

它将生成一个 hashcat 目标文件，格式为 `$metamask${salt}${iterations}${iv}${cypher}`，用于 hashcat 破解。
第二个参数是字典文件夹。随后会在仓库根目录生成 `run_bashcat.sh` 和 `run_hashcat.bat`，用于运行 hashcat。

**3. 使用 Hashcat 进行破解**

```bash
# 对于macos
bash run_hashcat.sh

# 对于windows
.\run_hashcat.bat
```

会一直运行，出现如下提示，按s会显示当前状态，按q退出。
```
[s]tatus [p]ause [b]ypass [c]heckpoint [f]inish [q]uit => 
# 按s后打印当前状态，比较重要的有
Status：当前状态，Running 表示正在运行，Exhausted 表示已经尝试完所有密码，Cracked 表示找到密码。
Time.Estimated：预计完成时间
Guess.Base：当前使用的字典
Speed.#2：当前速度，每秒尝试密码数
Progress：当前进度，尝试过的密码数
```
破解完成后，如果密码被找到，将显示 Status: Cracked，并且在前2行末尾会显示类似内容`sH3TV5Q0G0rEQ==:12345678`，表示`12345678` 是密码。
![结果展示](./docs/result.png)


> 如果你想知道如何设置安全的密码，可见 [Presentation](https://gist.github.com/leplatrem/b1f23563a3028c66276ddf48705fac84)

## 密码库

1. [RockYou](https://github.com/josuamarcelc/common-password-list/blob/main/rockyou.txt/rockyou.txt.zip)，不需要分离密码。来源于2009 年，RockYou 社交应用平台被攻击，约 3200 万个用户密码泄露。
2. [linkedin password](https://github.com/brannondorsey/PassGAN/releases/download/data/68_linkedin_found_hash_plain.txt.zip)， 需要分离密码。来源于 2012 年 LinkedIn 数据泄露事件，包含 1.6 亿用户的密码哈希。
3. [CrackStation](https://crackstation.net/crackstation-wordlist-password-cracking-dictionary.htm)，选择只有密码的那个，不需要分离密码。
4. [Collection #1](https://github.com/p4wnsolo/breach-torrents)，需要分离密码。解压后得到 `Collection #1` 文件夹，里面有多个tar.gz压缩文件。 `magnet:?xt=urn:btih:b39c603c7e18db8262067c5926e7d5ea5d20e12e&dn=Collection+1`。
5. Collection #2 - #5，解压后得到 `Collection 2-5 & Antipublic` 文件夹，里面有多个tar.gz压缩文件。`magnet:?xt=urn:btih:d136b1adde531f38311fbf43fb96fc26df1a34cd&dn=Collection+%232-%235+%26+Antipublic`

以下密码库未经过测试。

6. [BreachCompilation](https://github.com/p4wnsolo/breach-torrents)，2017 年，一个匿名用户通过 Torrents 将 BreachCompilation 数据库发布到互联网上。来源是各种已知的历史数据泄露事件（如 LinkedIn、MySpace、Adobe、Dropbox 等）。`magnet:?xt=urn:btih:7ffbcd8cee06aba2ce6561688cf68ce2addca0a3&dn=BreachCompilation&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969&tr=udp%3A%2F%2Fglotorrents.pw%3A6969&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337`, `magnet:?xt=urn:btih:7FFBCD8CEE06ABA2CE6561688CF68CE2ADDCA0A3&dn=BreachCompilation`

> 以上密码库均来自于公开渠道，仅供研究使用。

## 原理解读
博客 doing...

## TODO

- [ ] 解密 metamask ldb，实现任何情况获取助记词。
- [ ] 使用规则，从用户密码中生成更多可能的密码。
- [ ] 使用大模型或者深度学习推理chrome密码，生成用户自定义字典。 



## 常见问题
### No module named 'src'
请确保已经进入虚拟环境 `poetry shell`，并且在项目根目录下运行，而不是在其他目录下。
环境变量 `PYTHONPATH` 也需要指向项目根目录。

### 找不到依赖裤
问题类似于 `ModuleNotFoundError: No module named 'xxx'`，解决方法是
重新运行 `poetry install` 并且重新进入虚拟环境 `poetry shell`

### 无法找到 metamask vault

由于通过 chrome 本地存储的 metamask 日志解密，而不是根据完全加密后的 `.ldb` 解密，又无法预测日志删除时间，所以如果钱包长期未打开，可能会删除相关记录。

解决办法：再次打开 metamask 页面。

### 破解速度太慢

自从 metamask 密钥派生的 pdkdf2-sha256 的迭代次数，从 10000 变成了 600000，破解速度大大减慢。

对于 MacBook M4 pro 14+16，从 57736 H/s 变成了 968 H/s。meta API 和 OpenCL API差别不大。

4060 显卡当前约 2400 H/s。


> 个人博客：[blog-blockchain.xyz](https://blog-blockchain.xyz/) 更多好玩有趣的区块链技术文章。
