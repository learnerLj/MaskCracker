<div align="center">
<img src="logo.png" alt="hack-browser-data logo" width="440px" />
</div>
<p align="left">
  <a href="./README_en.md">English Version Here</a> 
</p>

这是一个用于解密存储在 Chrome 登录数据数据库中的密码的 Python 脚本，支持 MAC 和 windows。基本原理是从 chrome 本地 sqlite 数据库，读取 uri, username, password，并且模拟 chrome 的加密算法，使用 python 解密 password。

metamask hack 已经初步完成，但是由于vault的代码被加密了，目前在metamask 页面打开时候能实现，但是关闭后一段一时间**可能**会删除相关记录。后续进一步研究解密。

TODO:
- [ ] 解密 metamask ldb，实现任何情况获取助记词。
- [ ] 使用 chrome 网站密码，进行字典生成和破解。

> 免责声明：本工具仅用于安全研究，因使用本工具而产生的一切法律及相关责任由用户自行承担，原作者不承担任何法律责任。

## 功能解读
### 针对 chrome password
- get_login_data_paths：定位不同用户配置文件中的 Chrome 登录数据数据库文件。
- safe_storage_key：获取存储的密钥
  - 使用 Windows 的 DPAPI（Data Protection API）解密得到密钥
  - 从 macOS 密钥链中检索 Chrome 安全存储密钥，根据 chrome 源码用 python 实现密钥派生，得到真实密钥。
- chrome_decrypt：解密存储在 Chrome 登录数据数据库中的密码。
  - windows 使用 AES-128-GCM 算法，`[3:15]` 字节为初始向量，`[15:-16]` 为密码密文。
  - macOS 使用 AES-128-CBC 算法，16 字节 b"\x20" 是固定的初始向量，`[3:]` 字节为密码密文。

### 针对 metamask

doing

## 安装

该项目使用 Poetry 进行依赖管理，可参考[安装教程](https://python-poetry.org/docs/)。
要安装依赖，请确保已安装 Poetry，然后运行：

```bash
poetry install
```

## 使用方法

直接使用 poetry 运行，将在命令行输出。查看后请及时 `clear` 命令行。

```bash
poetry run python src/hack_chrome_password.py
```

也可以进入虚拟环境，然后运行

```bash
poetry shell
python hack_chrome_password.py
```

同理，在文件中修改成你的 password，运行 `poetry run python src/hack_metamask.py`

## 常见问题
### 找不到依赖裤
重新运行 `poetry install` 并且重新进入虚拟环境 `poetry shell`


> 个人博客：[blog-blockchain.xyz](https://blog-blockchain.xyz/)
> 我会分享如何实现，以及如何阅读 chrome 代码找到对应逻辑解密。后续更进一步，会分享浏览器钱包插件如何被一键式 hack。
