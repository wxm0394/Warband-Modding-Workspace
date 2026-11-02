import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Callable, Tuple, List
from core.context import ProjectContext

class BuildRunner:
    """负责调用 Module System 编译、解析错误行号、管理测试存档和拉起游戏"""

    @classmethod
    def run_build(cls, ctx: ProjectContext, output_callback: Optional[Callable[[str], None]] = None) -> Tuple[bool, str, List[dict]]:
        """
        运行编译脚本，返回: (成功布尔值, 完整输出文本, 解析出的错误列表[{file, line, message}])
        """
        source_dir = ctx.source_path
        if not source_dir.exists():
            return False, f"源码目录不存在: {source_dir}", []

        # 确定编译命令
        cmd = None
        if (source_dir / "build_module.sh").exists():
            cmd = ["bash", "build_module.sh"]
        elif (source_dir / "build_module.py").exists():
            cmd = ["python3", "build_module.py"]
        elif (source_dir / "build_module.bat").exists():
            cmd = ["wine", "cmd", "/c", "build_module.bat"]
        elif ctx.config.build_command:
            cmd = ctx.config.build_command.split()
        else:
            cmd = ["python3", "build_module.py"]

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=source_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
        except Exception as e:
            return False, f"启动编译进程失败: {e}", []

        output_lines = []
        parsed_errors = []
        # 正则匹配形如: File "module_troops.py", line 142
        err_regex = re.compile(r'File "([^"]+)", line (\d+)(?:, in (.+))?')

        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                output_lines.append(line)
                if output_callback:
                    output_callback(line)
                m = err_regex.search(line)
                if m:
                    parsed_errors.append({
                        "file": m.group(1),
                        "line": int(m.group(2)),
                        "scope": m.group(3) or ""
                    })

        exit_code = proc.poll()
        full_output = "".join(output_lines)
        success = (exit_code == 0)
        return success, full_output, parsed_errors

    @classmethod
    def launch_game(cls, ctx: ProjectContext) -> Tuple[bool, str]:
        """拉起游戏进程"""
        cmd_str = ctx.config.launch_command
        if not cmd_str:
            return False, "未配置 launch_command，请在项目设置中指定启动命令。"

        try:
            # 使用 nohup / 独立进程拉起，防止工作区关闭带崩游戏
            subprocess.Popen(
                cmd_str,
                shell=True,
                cwd=ctx.config.warband_root or str(ctx.module_path),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            return True, f"已执行启动命令: {cmd_str}"
        except Exception as e:
            return False, f"拉起游戏失败: {e}"

    @classmethod
    def prepare_clean_test_save(cls, ctx: ProjectContext, template_save_path: Path) -> Tuple[bool, str]:
        """为快速测试部署干净的测试存档模板"""
        save_dirs = [
            Path.home() / f".mbwarband/Savegames/{ctx.module_path.name}",
            Path.home() / f".wine/drive_c/users/{os.environ.get('USER', 'wxm')}/Documents/Mount&Blade Warband Savegames/{ctx.module_path.name}"
        ]
        target_dir = None
        for d in save_dirs:
            if d.parent.exists():
                target_dir = d
                break

        if not target_dir:
            target_dir = save_dirs[0]

        target_dir.mkdir(parents=True, exist_ok=True)
        dest_save = target_dir / "sg00.sav"
        try:
            shutil.copy2(template_save_path, dest_save)
            return True, f"已将测试存档就绪于: {dest_save}"
        except Exception as e:
            return False, f"部署测试存档失败: {e}"
