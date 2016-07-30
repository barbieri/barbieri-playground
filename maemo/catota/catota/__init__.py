import os
import stat

__all__ = ("which",)


def which(app):
    """function to implement which(1) unix command"""
    pl = os.environ["PATH"].split(os.pathsep)
    for p in pl:
        path = os.path.join(p, app)
        if os.path.isfile(path):
            st = os.stat(path)
            if st[stat.ST_MODE] & 0111:
                return path
    return ""
# which()
