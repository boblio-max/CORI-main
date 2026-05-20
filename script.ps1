# 1. Uninstall mediapipe
pip uninstall mediapipe -y

# 2. Delete ALL cache
Remove-Item -Recurse -Force __pycache__
Remove-Item -Recurse -Force .venv\Lib\site-packages\mediapipe
Remove-Item -Recurse -Force .venv\Lib\site-packages\mediapipe-*.dist-info

# 3. Reinstall
pip install mediapipe