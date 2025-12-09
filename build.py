import PyInstaller.__main__
import os
import shutil

# Clean build/dist
if os.path.exists('build'):
    shutil.rmtree('build')
if os.path.exists('dist'):
    shutil.rmtree('dist')

# Define paths
base_path = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.join(base_path, 'frontend')
app_script = os.path.join(base_path, 'app.py')

# PyInstaller arguments
args = [
    app_script,
    '--name=VantaSys',
    '--onefile',
    '--clean',
    '--noconfirm',
    f'--add-data={frontend_path};frontend',  # Windows format ;
    # For linux it would be :
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
]

print("Building VantaSys...")
PyInstaller.__main__.run(args)
print("Build complete. Executable is in dist/")
