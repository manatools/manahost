# vim: set fileencoding=utf-8 :
# vim: set et ts=4 sw=4:
'''
manahost is a graphical hostname configuration tool based on ManaTools AUI python

License: GPLv3

Author:  Angelo Naselli <anaselli@linux.it>

@package manahost
'''

from .app import main


if __name__ == "__main__":
    raise SystemExit(main())
