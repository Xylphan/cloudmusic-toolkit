# Cloudmusic Toolkit

网易云音乐本地文件管理工具

## 功能

| 命令      | 功能                                                                                                        |
| --------- | ----------------------------------------------------------------------------------------------------------- |
| `arrange` | 解析本地 MP3/FLAC 元数据，匹配网易云本地完整数据库并生成 163 key 嵌入音频注释块，确保准确识别，并按目录归类 |
| `check`   | 提取音频比特率并与数据库中的最高比特率对比，按自定义阈值筛除低音质文件                                      |
| `sync`    | 集成 FFmpeg 进行音频转码，同时转换元数据，比对时间戳实现增量同步MP3                                         |

## 环境

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

使用 `arrange` 命令需下载 [ncmdump](https://github.com/taurusxin/ncmdump/releases/latest) 并将 ncmdump.exe 放到 `./bin` 目录中

使用 `sync` 命令需下载 [ffmpeg](https://ffmpeg.org/download.html) 并将其添加至环境变量

## 配置

将根目录的 `.env.example` 文件重命名为 `.env` ，设置以下配置项：

| 配置项       | 说明                               |
| ------------ | ---------------------------------- |
| `PATH`       | 网易云音乐下载目录                 |
| `USER_AGENT` | 请求网易云 API 时使用的 User-Agent |
| `SYNC_PATH`  | `sync` 命令的输出目录              |

## 使用

```batch
run arrange
run check
run sync
```

## 致谢

网易云 API 请求参考 [NeteaseCloudMusicApiEnhanced](https://github.com/NeteaseCloudMusicApiEnhanced/api-enhanced)

## License

MIT
