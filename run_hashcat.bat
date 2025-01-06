@echo off
pushd "C:\hash\hashcat-6.2.4"
hashcat.exe %*
popd