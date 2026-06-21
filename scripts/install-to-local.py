# encoding=utf-8

import os
import sys
import shutil
import fire

def main():
    if os.path.exists("xnote_web.egg-info"):
        shutil.rmtree("xnote_web.egg-info")

    dist_dir = "dist"
    for fname in os.listdir(dist_dir):
        fpath = os.path.join(dist_dir, fname)
        print(f"removing {fpath}")
        os.remove(fpath)

    os.system(f"{sys.executable} setup.py sdist")
    for fname in os.listdir("dist"):
        if fname.endswith(".tar.gz"):
            os.system(f"{sys.executable} -m pip install dist/{fname}")

if __name__ == "__main__":
    fire.Fire(main)