# 站立提醒工具

一个 Windows 托盘常驻小工具，会在设定的上班时间内按固定间隔弹窗提醒站立活动。

## 运行

```powershell
& "C:\Users\UserName\AppData\Local\Programs\Python\Python314\python.exe" .\main.py
```

## 打包

双击 `build_exe.bat`，或在 PowerShell 中执行：

```powershell
.\build_exe.bat
```

打包完成后，exe 位于：

```text
dist\StandingReminder.exe
```

打包脚本会先生成 `assets\app_icon.ico`，再通过 `StandingReminder.spec` 把程序和 `assets\standing_mascot.png` 一起打进 exe。

## 功能

- 工作时间开始/结束可配置
- 默认每 60 分钟提醒一次
- 弹窗展示轻松提示语和可爱 PNG 插图
- 点击“已站立”后隐藏窗口
- 提醒弹窗不能手动关闭，避免误操作被当作已站立
- 程序隐藏时继续停留在系统托盘
- 重复启动时不会创建多个进程
- 托盘菜单支持暂停 1 小时、今日不再提醒和恢复提醒
- 可在设置中开启或关闭开机自启动

## 配置

配置会保存到当前用户的应用配置目录。程序启动时会校验配置文件，如果时间格式或提醒间隔异常，会自动回退到默认值。

开机自启动使用当前用户的 Windows 启动项，不需要管理员权限。勾选或取消勾选后会立即生效。

## 开发检查

```powershell
python -m py_compile main.py config.py reminder.py startup.py widgets.py create_icon.py
```

```powershell
python -m unittest discover -s tests
```
