# Trade_analysis

把自己的交易分析系统，逐步搭起来。

## 开发环境

- 后端目录：`trade_analysis_backend`
- 前端目录：`trade_analysis_web`
- 后端虚拟环境：`trade_analysis_backend\.venv`

## 根目录启动

打开两个终端，分别在项目根目录执行：

```powershell
npm.cmd run dev:backend
```

```powershell
npm.cmd run dev:web
```

如果你的 PowerShell 已允许执行 `npm`，也可以把 `npm.cmd` 换成 `npm`：

```powershell
npm run dev:backend
npm run dev:web
```

这两个命令会分别启动：

- 后端：`fastapi dev main.py`
- 前端：`npm run dev`

## 常用命令

只启动后端：

```powershell
npm.cmd run dev:backend
```

只启动前端：

```powershell
npm.cmd run dev:web
```
