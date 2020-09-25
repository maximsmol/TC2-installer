pyinstaller -ywF -i icon.ico -n 'TC2 Installer' --add-data "src\safe_cfgs.txt;." --add-data "src\gh_markdown.css;." --add-data "src\tf2_paths.txt;." src\main.py
