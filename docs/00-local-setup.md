# 本地跑通指南（Windows）

> 目标：在自己的机器上把 8 个案例跑起来。**不需要 6 家模型厂商的 Key**，一个就行。

## 0. 前置检查

```powershell
docker --version          # 需要 Docker Desktop 已安装
docker info               # 关键：这条能返回信息，说明守护进程起来了
```

如果 `docker info` 报 `cannot find the pipe dockerDesktopLinuxEngine`，说明 Docker Desktop 没启动：

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# 等 30-60 秒，直到托盘鲸鱼图标稳定，再执行 docker info
```

硬件建议：可用内存 ≥ 8GB，磁盘留 ≥ 15GB（镜像约 5GB）。

## 1. 启动 Dify

如果你已经有 Dify 源码（本仓库配套环境在 `DifyProjects\dify`），直接用，**省掉一次 1GB+ 的 clone**：

```powershell
cd C:\Users\cheny\Desktop\Dify\DifyProjects\dify\docker
docker compose up -d
```

首次会拉取约 3GB 镜像，视网络 5-20 分钟。完成后：

```powershell
docker compose ps          # 等 api / worker / web / nginx / sandbox / plugin_daemon 都 running
```

浏览器打开 <http://localhost/install>，设置管理员邮箱与密码。

> 没有源码的话先 `git clone https://github.com/langgenius/dify.git`，再进 `dify\docker`。
> 端口 80 被占用时，改 `.env` 里的 `EXPOSE_NGINX_PORT=8080`，然后访问 <http://localhost:8080>。

## 2. 选对首跑顺序（别一上来跑研究 Agent）

| 顺序 | 案例 | 前置条件 | 预计 | 用途 |
| --- | --- | --- | --- | --- |
| ① | `jieba-tokenizer` | 无模型、无插件 | 2 分钟 | 验证"导入 → 运行"链路是否通 |
| ② | `tod-slot-agent` | 1 个模型 | 5 分钟 | 验证 Agent 策略插件能否装上 |
| ③ | **`nlp2sql-analytics-agent`** | 1 个模型 + MySQL + 2 个插件 | 30 分钟 | **最值得跑，完整闭环** |
| ④ | `rag-doc-chat` | 1 个模型 + 1 个知识库 | 20 分钟 | 验证 RAG 路由 |
| ⑤ | `deep-researcher` | 1 个模型 + 知识库 + Wikipedia 插件 | 40 分钟 | 节点最多，坑也最多 |
| ⑥ | `web-research-agent` | 1 个模型 + 搜索/爬虫插件 | 20 分钟 | 需要外网可达 |
| ⑦ | `code-translator` | 2 个模型 + AWS Lambda 插件 | — | 插件可能装不上，可跳过 |

导入方式：Dify 控制台 → **工作室** → 右上角「导入 DSL 文件」→ 选 `agent-lab\apps\xxx.yml`。

## 3. 配模型：一个就够

DSL 里保存的只是**模型标识**，不含密钥。导入后节点大概率标红「模型不存在」。

**最省事的做法**：装一个供应商，然后把节点里的模型全换成它。推荐 DeepSeek（国内直连、便宜、够用）。

设置 → 模型供应商 → 找到 DeepSeek → 安装 → 填 API Key。

然后逐个打开红色节点，在「模型」下拉里改成 `deepseek-chat`。

各案例原始模型与替换建议：

| 案例 | 原模型 | 建议替换 |
| --- | --- | --- |
| `nlp2sql` | `deepseek-chat` | 无需替换 ✅ |
| `tod-slot-agent` | `o1-mini` | `deepseek-chat` |
| `deep-researcher` | `gemini-2.0-flash-exp` / `deepseek-r1-distill-llama-8b` | 全部 `deepseek-chat` |
| `memory-agent` | `Doubao-Pro-32k` / `qwen-vl-plus` | 文本换 `deepseek-chat`；图片节点需多模态模型，没有就删掉那条分支 |
| `web-research-agent` | Bedrock Claude 3.5 | `deepseek-chat` |
| `rag-doc-chat` | `deepseek-chat` | 无需替换 ✅ |
| `code-translator` | Bedrock Claude 3.5 / 3 | `deepseek-chat` |

> 换模型时注意：原来靠 `o1-mini` 推理能力的提示词，换成小模型后可能效果变差，属于正常现象，不影响"跑通"。

## 4. 跑通 NL2SQL（重点）

### 4.1 起一个 MySQL

```powershell
docker run -d --name mysql-demo `
  -p 3306:3306 `
  -e MYSQL_ROOT_PASSWORD=demo123 `
  -e MYSQL_DATABASE=dify_test `
  mysql:8.0
```

等 20 秒让它初始化完成，然后导入表和数据。

> ⚠️ PowerShell 不支持 `cmd < file` 这种重定向，必须用管道：

```powershell
cd C:\Users\cheny\Desktop\Dify

Get-Content -Raw .\agent-lab\data\schema.sql | docker exec -i mysql-demo mysql -uroot -pdemo123 dify_test
Get-Content -Raw .\agent-lab\data\seed.sql   | docker exec -i mysql-demo mysql -uroot -pdemo123 dify_test

# 校验：应返回 110
docker exec -i mysql-demo mysql -uroot -pdemo123 dify_test -e "SELECT COUNT(*) FROM student_grades;"
```

### 4.2 装插件

设置 → 插件市场，搜索并安装：

- `hjlarry/database`（提供 SQL Execute 工具）
- `langgenius/echarts`（提供折线/柱状/饼图工具）

### 4.3 填数据库连接

打开 `nlp2sql-analytics-agent`，找到 **SQL Execute** 工具节点，`db_uri` 填：

```
mysql+pymysql://root:demo123@host.docker.internal:3306/dify_test
```

> ⚠️ **最容易卡住的地方**：插件跑在容器里，`127.0.0.1` 指向的是容器自己，不是你的电脑。
> 必须用 `host.docker.internal`（Docker Desktop 提供的主机别名）。
> 如果仍连不上，试 `172.17.0.1`，或把 MySQL 也加入 Dify 的 Docker 网络后直接用容器名。

### 4.4 提问

新建对话，输入：

> 查询全校各科目平均分情况

预期：先出几段进度提示，然后一张按科目分组的柱状图 + Markdown 结论。

## 5. 跑通研究 Agent（可选，坑最多）

1. **建知识库**：知识库 → 创建 → 上传几篇 md / pdf → 等索引进度到 100%。
2. **重新绑定知识库**：打开 `deep-researcher`，点每个「知识检索」节点，重新选择你刚建的知识库。
   > ⚠️ DSL 里存的是原作者的 `dataset_id`（一串 UUID），你机器上不存在，**必然失效**，必须手动重选。
3. **装 Wikipedia 插件**：插件市场搜 `wikipedia`。
4. **统一模型**：把 `gemini-2.0-flash-exp` 和 `deepseek-r1-distill-llama-8b` 全换成 `deepseek-chat`。
5. 输入一个研究主题，按提示回答 4 轮问题，等报告生成。

## 6. 排错表

| 现象 | 原因 | 解决 |
| --- | --- | --- |
| `docker info` 报 pipe 不存在 | Docker Desktop 未启动 | 启动并等鲸鱼图标稳定 |
| 导入报 DSL 版本不兼容 | 你的 Dify 太旧 | 升级到 1.x；本仓库 DSL 为 `0.1.5`，Dify 1.15 一般可直接导入 |
| 节点标红「模型不存在」 | 未配置对应供应商 | 按第 3 节换模型 |
| 知识检索节点报 `dataset not found` | `dataset_id` 失效 | 重新选择知识库 |
| SQL Execute 连接超时 | 用了 `127.0.0.1` | 改 `host.docker.internal` |
| SQL Execute 认证失败 | 密码错 / 库不存在 | 先 `docker exec` 进去手动连一次验证 |
| 插件市场搜不到 `hjlarry/database` | 网络无法访问插件源 | 改用 HTTP 请求节点调自建接口，或跳过该案例 |
| 代码节点报 `ImportError: jieba` | 沙箱镜像未预装该库 | 跳过 `jieba-tokenizer`，只作示例 |
| 页面打不开 | 端口 80 被占 | `.env` 里 `EXPOSE_NGINX_PORT=8080` 后重启 |
| 镜像拉取很慢 | 网络 | 配 Docker 镜像加速器后重试 |

查看容器日志定位问题：

```powershell
docker compose logs -f api      # 或 worker / plugin_daemon / sandbox
```

## 7. 怎么算"跑通了"

- [ ] `docker compose ps` 里核心服务都是 `running`
- [ ] <http://localhost> 能正常登录
- [ ] 导入的 DSL 在画布上**没有红色节点**
- [ ] 对话能出结果（哪怕内容不完美）
- [ ] Dify 的「追踪 / 日志」面板能看到每个节点的耗时与输入输出

最后一项最容易被忽略 —— **只有能在追踪面板里看到节点级数据，才算真的跑通**，否则你只是看到了一个不报错的空壳。

## 8. 时间预算

| 阶段 | 耗时 |
| --- | --- |
| 启动 Docker Desktop | 1 分钟 |
| 拉镜像 + 起 Dify | 10-20 分钟（下载占大头） |
| 导入 + 配模型 + 跑通 `jieba` / `tod` | 10 分钟 |
| NL2SQL 全套 | 30 分钟 |
| 研究 Agent（含建知识库） | 40-60 分钟 |

**只想快速看一眼效果**：用 Dify Cloud（<https://cloud.dify.ai>）导入 `nlp2sql` 即可跳过 Docker，但插件与知识库有配额限制，部分案例跑不全。
