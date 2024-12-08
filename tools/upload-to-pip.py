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

    os.system(f"{sys.executable} setup.py")
    os.system(f"{sys.executable} -m twine upload --username __token__ --paasword {pypi_token}")

if __name__ == "__main__":
    fire.Fire(main)