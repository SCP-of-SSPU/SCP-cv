# 第三方可执行文件约定

阶段一需要的第三方程序建议放在本目录下，或者通过环境变量写入其绝对路径。

## 目录结构

- `mediamtx/`：MediaMTX 解压目录
- `libreoffice/`：LibreOffice 相关文件或安装说明

## 环境变量

- `MEDIAMTX_BIN_PATH`
- `LIBREOFFICE_BIN_PATH`

如果没有写入环境变量，Django 服务会尝试从系统 `PATH` 中查找 `mediamtx` 和 `soffice`。
