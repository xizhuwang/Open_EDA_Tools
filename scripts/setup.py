"""Download a hash-verified, portable EDA distribution. No sudo/system edits."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    if platform.system() != 'Linux':
        raise SystemExit('Run this command inside Ubuntu WSL2/Linux, not PowerShell.')
    if str(ROOT).startswith('/mnt/'):
        raise SystemExit('Clone this project into the WSL Linux filesystem (e.g. ~/Open_EDA_Tools), not /mnt/c. AppImage extraction needs Linux symlinks and permissions.')
    lock = json.loads((ROOT / 'toolchain.lock.json').read_text())
    arch = platform.machine()
    if arch not in lock['assets']:
        raise SystemExit(f'Unsupported architecture: {arch}')
    asset = lock['assets'][arch]
    directory = ROOT / '.tools' / arch
    directory.mkdir(parents=True, exist_ok=True)
    image = directory / asset['filename']
    # Also accept a manually downloaded file in .tools, but still hash-check it.
    for candidate in [ROOT / '.tools' / asset['filename'], ROOT / '.tools' / (asset['filename'] + '.part')]:
        if not image.exists() and candidate.exists() and sha256(candidate) == asset['sha256']:
            shutil.move(str(candidate), image)
    if not image.exists():
        url = f'https://github.com/librelane/librelane/releases/download/{lock["version"]}/{asset["filename"]}'
        print(f'Downloading {lock["version"]}: about 1.4 GB; extraction needs several GB.', flush=True)
        partial = image.with_suffix('.partial')
        urllib.request.urlretrieve(url, partial)
        if sha256(partial) != asset['sha256']:
            raise SystemExit(f'Checksum mismatch; not executing {partial}. Remove it and retry.')
        partial.replace(image)
    if sha256(image) != asset['sha256']:
        raise SystemExit('Checksum mismatch. Refusing to execute the tool distribution.')
    image.chmod(0o755)
    marker = directory / 'verified.json'
    extraction = directory / 'squashfs-root'
    if not marker.exists():
        if extraction.exists():
            raise SystemExit(f'Incomplete extraction at {extraction}. Move it aside and retry.')
        print('Extracting once (no FUSE, Docker or root required)...', flush=True)
        with (directory / 'extract.log').open('w') as log:
            subprocess.run([str(image), '--appimage-extract'], cwd=directory, stdout=log, stderr=subprocess.STDOUT, check=True)
        marker.write_text(json.dumps({'version': lock['version'], 'sha256': asset['sha256']}, indent=2))
    (ROOT / 'eda').chmod(0o755)
    print('Testing the portable environment...', flush=True)
    env = dict(os.environ, EDA_ENV_ACTIVE='1', EDA_ROOT=str(ROOT))
    result = subprocess.run([str(extraction / 'AppRun'), 'python3', str(ROOT / 'eda.py'), 'doctor'], env=env)
    if result.returncode:
        print('See docs/WSL.md. No AppArmor or system security setting was modified.')
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
