# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime

import xbmc
import xbmcaddon
import xbmcgui
import xbmcvfs

ADDON = xbmcaddon.Addon()
ADDON_ID = ADDON.getAddonInfo("id")
SKIN_ID = "skin.arctic.fuse.3"
SKINVARS_ID = "script.skinvariables"
NODES_DIR = "special://profile/addon_data/script.skinvariables/nodes/skin.arctic.fuse.3/"
SHORTCUTS = "special://home/addons/{0}/resources/shortcuts/".format(ADDON_ID)
BACKUPS = "special://profile/addon_data/{0}/backups/".format(ADDON_ID)


def loc(string_id, fallback=""):
    value = ADDON.getLocalizedString(string_id)
    return value or fallback or str(string_id)


def dialog():
    return xbmcgui.Dialog()


def addon_exists(addon_id):
    try:
        xbmcaddon.Addon(addon_id)
        return True
    except RuntimeError:
        return False


def slash(path):
    path = path.replace("\\", "/")
    if not path.endswith("/"):
        path += "/"
    return path


def exists(path):
    return bool(xbmcvfs.exists(path) or xbmcvfs.exists(slash(path)))


def list_dir(path):
    path = slash(path)
    try:
        dirs, files = xbmcvfs.listdir(path)
    except Exception:
        return [], []
    return list(dirs), list(files)


def copy_tree(src, dst):
    src, dst = slash(src), slash(dst)
    xbmcvfs.mkdirs(dst)
    dirs, files = list_dir(src)
    for name in files:
        if not xbmcvfs.copy(src + name, dst + name):
            raise IOError("Cannot copy {0}".format(src + name))
    for name in dirs:
        copy_tree(src + name, dst + name)


def folder_has_files(path):
    dirs, files = list_dir(path)
    if files:
        return True
    return any(folder_has_files(slash(path) + name) for name in dirs)


def stamp():
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def rebuild_and_reload():
    when = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
    xbmc.executebuiltin("Skin.SetString(Shortcuts.RebuildDateTime,{0})".format(when))
    # Give skinvariables a moment to finish writing, then reload.
    xbmc.executebuiltin("AlarmClock(arnostlayout,ReloadSkin(),00:02,silent)")


def run_copy_menufolder(folder):
    folder = slash(folder)
    cmd = (
        "RunScript({0},copy_menufolder={1},skin={2},force=True)".format(
            SKINVARS_ID, folder, SKIN_ID
        )
    )
    xbmc.executebuiltin(cmd, True)


def check_environment():
    if xbmc.getSkinDir() != SKIN_ID:
        dialog().ok(loc(32000, "Rozvržení"), loc(32010, "Nejdřív zapněte vzhled Arctic Fuse 3."))
        return False
    if not addon_exists(SKINVARS_ID):
        dialog().ok(loc(32000, "Rozvržení"), loc(32011, "Chybí doplněk Skin Variables, bez něj vzhled neumí uložit řady."))
        return False
    if not addon_exists("plugin.video.cztor"):
        if not dialog().yesno(
            loc(32000, "Rozvržení"),
            loc(32012, "Video doplněk, ze kterého řady čerpají, není nainstalovaný. Řady mohou zůstat prázdné. Přesto pokračovat?"),
        ):
            return False
    return True


def make_backup():
    if not exists(NODES_DIR) or not folder_has_files(NODES_DIR):
        return ""
    name = stamp()
    dest = slash(BACKUPS) + name + "/"
    xbmcvfs.mkdirs(dest)
    copy_tree(NODES_DIR, dest)
    return name


def apply_layout():
    if not dialog().yesno(
        loc(32000, "Rozvržení"),
        loc(32020, "Nahradí aktuální řady na domovské obrazovce. Nejdřív se vytvoří záloha. Pokračovat?"),
    ):
        return
    if not check_environment():
        return
    try:
        backup = make_backup()
        run_copy_menufolder(SHORTCUTS)
    except Exception as exc:
        dialog().ok(loc(32000, "Rozvržení"), loc(32021, "Záloha nebo zápis se nepovedly: {0}").format(exc))
        return
    rebuild_and_reload()
    if backup:
        dialog().ok(
            loc(32000, "Rozvržení"),
            loc(32022, "Rozvržení je nastavené. Záloha: {0}. Obrazovka se za chvíli znovu načte.").format(backup),
        )
    else:
        dialog().ok(loc(32000, "Rozvržení"), loc(32023, "Rozvržení je nastavené. Obrazovka se za chvíli znovu načte."))


def list_backups():
    xbmcvfs.mkdirs(BACKUPS)
    dirs, _files = list_dir(BACKUPS)
    return sorted((name for name in dirs if name), reverse=True)


def restore_backup():
    if not check_environment():
        return
    names = list_backups()
    if not names:
        dialog().ok(loc(32000, "Rozvržení"), loc(32030, "Žádná záloha zatím není."))
        return
    choice = dialog().select(loc(32031, "Vyberte zálohu"), names)
    if choice < 0:
        return
    name = names[choice]
    if not dialog().yesno(
        loc(32000, "Rozvržení"),
        loc(32032, "Obnovit zálohu {0}? Aktuální řady se přepíšou.").format(name),
    ):
        return
    # Keep a safety copy of the state we are about to replace.
    try:
        make_backup()
        run_copy_menufolder(slash(BACKUPS) + name + "/")
    except Exception as exc:
        dialog().ok(loc(32000, "Rozvržení"), loc(32033, "Obnova se nepovedla: {0}").format(exc))
        return
    rebuild_and_reload()
    dialog().ok(loc(32000, "Rozvržení"), loc(32034, "Záloha je obnovená. Obrazovka se za chvíli znovu načte."))


def main():
    choice = dialog().select(
        loc(32000, "Rozvržení"),
        [loc(32001, "Použít rozvržení"), loc(32002, "Obnovit zálohu"), loc(32003, "Zrušit")],
    )
    if choice == 0:
        apply_layout()
    elif choice == 1:
        restore_backup()


if __name__ == "__main__":
    main()
