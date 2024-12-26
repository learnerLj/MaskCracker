


# hackChromePassword

这是一个用于解密存储在 Chrome 登录数据数据库中的密码的 Python 脚本，支持 MAC 和 windows。基本原理是从本地读取加密后的uri, username, password，并且模拟chrome的加密算法，使用python解密。

## 功能

- 定位不同用户配置文件中的 Chrome 登录数据数据库文件。
- 从 macOS 密钥链中检索 Chrome 安全存储密钥。
- 解密存储在 Chrome 登录数据数据库中的密码。

## 安装

该项目使用 Poetry 进行依赖管理。要安装依赖，请确保已安装 Poetry，然后运行：
```bash
poetry install
```

## 使用方法
直接使用 poetry运行
```bash
poetry run python main.py
```
也可以进入虚拟环境，然后运行
```bash
poetry shell
python main
```

## 联系方式

如有任何问题，请通过以下电子邮件与我联系：luoshitou9@gmail.com

## 许可证

本项目采用 MIT 许可证。请查看项目中的 LICENSE 文件以获取更多信息。