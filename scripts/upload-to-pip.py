# encoding=utf-8

import os
import sys
import shutil
import fire

def main():
    with open("pypi_token.txt", "r+") as fp:
        pypi_token = fp.read()

    if os.path.exists("xnote_web.egg-info"):
        shutil.rmtree("xnote_web.egg-info")

    dist_dir = "dist"
    for fname in os.listdir(dist_dir):
        fpath = os.path.join(dist_dir, fname)
        print(f"removing {fpath}")
        os.remove(fpath)

    os.system(f"{sys.executable} setup.py sdist")
    os.system(f"{sys.executable} -m twine upload --username __token__ --password {pypi_token} dist/*")

if __name__ == "__main__":
    fire.Fire(main)