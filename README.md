# 站立提醒工具

一个 Windows 托盘常驻小工具，会在设定的上班时间内按固定间隔弹窗提醒站立活动。

## 运行

```powershell
& "C:\Users\Chen\AppData\Local\Programs\Python\Python314\python.exe" .\main.py
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

## 功能

- 工作时间开始/结束可配置
- 默认每 3 分钟提醒一次
- 弹窗展示轻松提示语和可爱插图
- 点击“已站立”后隐藏窗口
- 程序隐藏时继续停留在系统托盘
- 重复启动时不会创建多个进程
