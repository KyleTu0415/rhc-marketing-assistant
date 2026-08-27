# RHC Medical 外贸营销中心

宠物医疗器械外贸营销内容生成平台。

## 功能

- AI 背景图生成（Coze 工作流）
- 动物图片素材搜索（Unsplash）
- 文字卡片生成
- 多图层排版合成
- 历史记录管理

## 项目结构

```
rhc-marketing-assistant/
├── backend/          # FastAPI 后端
│   ├── app/
│   │   ├── main.py          # 主应用
│   │   ├── composer.py      # 图片合成引擎
│   │   └── config.py        # 配置管理
│   ├── requirements.txt
│   ├── Procfile
│   └── .env.example
└── frontend/         # 前端页面
    └── index.html    # 单文件完整应用
```

## 本地运行

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

直接用浏览器打开 `frontend/index.html`

## 部署

### Railway（后端）

1. 安装 Railway CLI: `npm i -g @railway/cli`
2. 登录: `railway login`
3. 初始化: `railway init`
4. 设置环境变量:
   ```bash
   railway variables set COZE_PAT=your_pat
   railway variables set COZE_WORKFLOW_ID=7673785423382331442
   ```
5. 部署: `railway up`

### Netlify（前端）

1. 登录 Netlify Dashboard
2. 拖拽 `frontend/` 文件夹到部署区域
3. 部署后修改 `index.html` 中的 API 地址为 Railway URL

## 环境变量

| 变量名 | 说明 | 必填 |
|--------|------|------|
| COZE_PAT | Coze Personal Access Token | ✅ |
| COZE_WORKFLOW_ID | Coze 工作流 ID | ✅ |
| OPENAI_API_KEY | OpenAI/DeepSeek API Key | 可选 |

## 技术栈

- 后端：Python 3.11 + FastAPI + Pillow
- 前端：原生 HTML + CSS + JavaScript
- AI：Coze 工作流 + Unsplash API
