import os
import platform

def osname():
    return os.name

def iswindows():
    return os.name == "nt"

def ismac():
    return platform.system() == "Darwin"

def islinux():
    return os.name == "linux"

# TODO