import os
import sys
import gettext
import inspect
import builtins
from pathlib import Path


def init_gettext(locale_dir, locale_name):
    gettext.bindtextdomain('fr', locale_dir)
    gettext.textdomain('fr')
    os.environ['LANG'] = 'fr_FR.UTF-8'
    return gettext.gettext


execute_dir = os.path.split(os.path.realpath(sys.argv[0]))[0]
if os.path.exists(Path(execute_dir) / '_internal/i18n'):
    locale_path = Path(execute_dir) / '_internal/i18n'
else:
    locale_path = Path(execute_dir) / 'i18n'
_tr = init_gettext(locale_path, 'fr')
original_print = builtins.print
package_name = 'src'


def translated_print(*args, **kwargs):
    for arg in args:
        if package_name in inspect.stack()[1].filename:
            translated_arg = _tr(str(arg))
        else:
            translated_arg = str(arg)
        original_print(translated_arg, **kwargs)
