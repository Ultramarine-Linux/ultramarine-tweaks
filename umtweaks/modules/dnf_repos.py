import subprocess
import os
from typing import Any
from umtweaks.widgets import BooleanOption, IntegerRangeOption, TextOption
from . import Module

from gi.repository import Gtk, GObject

# TODO: Add a polkit rule for this module, else it will not work thanks to permissions

import configparser


class YumRepo:
    def __init__(self):
        self.name: str = ""
        self.id: str = ""
        self.enabled: bool = True
        self.gpgcheck: bool = True
        self.gpgkey: str = ""
        self.enabled_metadata: bool = True
        self.type: str = "rpm-md"  # Make this an enum?
        self.baseurl: str = ""
        self.metalink: str = ""
        self.skip_if_unavailable: bool = False
        self.defaultyes: bool = False
        self.boolean_options = [
            "enabled",
            "gpgcheck",
            "enabled_metadata",
            "skip_if_unavailable",
            "defaultyes",
            "defaultno",
        ]
        self.files: list[str] = []

    def set(self, attr: str, value: Any):
        setattr(self, attr, value)

    def get(self, attr: str):
        return getattr(self, attr)

    @staticmethod
    def from_config(file: str):
        config = configparser.ConfigParser()
        config.read(file)
        # for section in config.sections():
        for section in config.sections():
            # Get section name
            repo_id = section
            repo = YumRepo()
            repo.set("id", repo_id)
            for option in config.options(section):
                if option in repo.boolean_options:
                    value = config.getboolean(section, option)
                    repo.set(option, value)
                else:
                    repo.set(option, config.get(section, option))
            return repo

    @staticmethod
    def from_repos():
        repos: list[YumRepo] = []
        repos_folder = "/etc/yum.repos.d/"
        for file in os.listdir(repos_folder):
            if file.endswith(".repo"):
                assert (repo := YumRepo.from_config(repos_folder + file))
                repo.files.append(repos_folder + file)
                repos.append(repo)
        return repos

    @staticmethod
    def find_from_id(id: str):
        repos = YumRepo.from_repos()
        for repo in repos:
            if repo.id == id:
                return repo
        return None

    def set_config(self, id: str, option: str, value: str):
        config = configparser.ConfigParser()
        config.read(self.files[0])
        config.set(id, option, value)
        with open(self.files[0], "w") as configfile:
            config.write(configfile)

    def set_boolean(self, id: str, option: str, value: bool):
        self.set_config(id, option, "1" if value else "0")


class ReposModule(Module):
    """Test Module"""

    def __init__(self):
        super().__init__()
        self.name = "Repositories"
        self.description = "This is a test module"
        self.icon = "system-software-install-symbolic"
        self.treeview = Gtk.TreeView()

        # Create the model
        self.treeview_model = Gtk.ListStore(str, str, str, bool)
        self.treeview.set_model(self.treeview_model)

        # Create the TreeViewColumns to display the data
        id_column = Gtk.TreeViewColumn("ID")
        self.treeview.append_column(id_column)
        id_cell = Gtk.CellRendererText()
        id_column.pack_start(id_cell, True)
        id_column.add_attribute(id_cell, "text", 0)
        # set size of column
        id_column.set_fixed_width(100)
        # make resizable
        id_column.set_resizable(True)

        name_column = Gtk.TreeViewColumn("Name")
        self.treeview.append_column(name_column)
        name_cell = Gtk.CellRendererText()
        name_column.pack_start(name_cell, True)
        name_column.add_attribute(name_cell, "text", 1)
        # set size of column
        name_column.set_min_width(100)
        name_column.set_fixed_width(300)
        # make resizable
        name_column.set_resizable(True)

        baseurl_column = Gtk.TreeViewColumn("Base URL")
        self.treeview.append_column(baseurl_column)
        baseurl_cell = Gtk.CellRendererText()
        baseurl_column.pack_start(baseurl_cell, True)
        baseurl_column.add_attribute(baseurl_cell, "text", 2)
        # set size of column
        baseurl_column.set_fixed_width(200)
        # hexpand the column
        baseurl_column.set_expand(True)
        # make resizable
        baseurl_column.set_resizable(True)

        # checkbox for enabled
        enabled_column = Gtk.TreeViewColumn("Enabled")
        self.treeview.append_column(enabled_column)
        enabled_cell = Gtk.CellRendererToggle()
        enabled_column.pack_start(enabled_cell, True)
        enabled_column.add_attribute(enabled_cell, "active", 3)
        # align checkbox to the right
        enabled_column.set_alignment(1)
        # set size of column
        enabled_column.set_fixed_width(50)
        # make resizable
        enabled_column.set_resizable(True)

        # Add the rows
        self.repolist = YumRepo.from_repos()
        for repo in self.repolist:
            self.treeview_model.append([repo.id, repo.name, repo.baseurl, repo.enabled])

        # fix size for treeview row
        # self.treeview.set_fixed_height_mode(True)
        self.treeview.set_size_request(-1, 200)

        self.page.add_row(self.treeview)

        self.treeview.connect("row-activated", self.on_row_activated)

        # Get currently selected row
        self.selected_row: YumRepo = None

        # Rows for options

        self.repo_name_row = TextOption(
            title="Repository Name",
            description="Name of the repository",
            text=self.selected_row.name if self.selected_row else "",
        )

        self.page.add_row(self.repo_name_row)

        self.baseurl_row = TextOption(
            title="Base URL",
            description="Base URL of the repository",
            text=self.selected_row.baseurl if self.selected_row else "",
            set_action=self.set_baseurl,
        )

        self.page.add_row(self.baseurl_row)

        self.mirrorurl_row = TextOption(
            title="Mirror URL",
            description="Mirror URL of the repository",
            text=self.selected_row.metalink if self.selected_row else "",
            set_action=self.set_mirrorurl,
        )

        self.page.add_row(self.mirrorurl_row)

        self.enabled_row = BooleanOption(
            title="Enabled",
            description="Enable or disable the repository",
            bool_value=self.selected_row.enabled if self.selected_row else False,
            set_action=self.set_enabled,
        )

        self.page.add_row(self.enabled_row)

        self.maxparallel = IntegerRangeOption(
            "Max Parallel Downloads (global)",
            "Maximum number of parallel downloads",
            1, 20, 1,
            self.set_max_parallel,
        )

        self.page.add_row(self.maxparallel)
        self.maxparallel.set_int(self.max_parallel())

        self.fastestmirror = BooleanOption(
            title="DNF fastestmirror (global)",
            description="Enable or disable fastestmirror",
            bool_value=self._fastest_mirror(),
            set_action=self.set_fastest_mirror,
        )

        self.page.add_row(self.fastestmirror)

    def set_max_parallel(self, widget: Gtk.SpinButton, _: GObject.GType | None = None):
        maxparallel = widget.get_value_as_int()
        self._global_cfg("max_parallel_downloads", str(maxparallel))
    
    def max_parallel(self):
        ret = self._global_cfg("max_parallel_downloads")
        if ret == '':
            self.maxparallel.set_sensitive(False)
            self.maxparallel.set_int(3)
            return 3
        try:
            return int(ret)
        except ValueError:
            self.maxparallel.set_int(3)
            self.set_max_parallel(self.maxparallel.spin, None)
            return 3

    def set_fastest_mirror(self, widget: Gtk.Switch, _: GObject.GType | None):
        self._fastest_mirror(self.fastestmirror.get_active())

    def _global_cfg(self, option: str, value: str|None = None):
        parser = configparser.ConfigParser()
        parser.read(os.path.expanduser("/etc/dnf/dnf.conf"))
        if value is not None:
            parser.set("main", option, value)
            f = open(os.path.expanduser("/etc/dnf/dnf.conf"), "w")
            f.write('# see `man dnf.conf` for defaults and possible options\n'
            '# If you use Ultramarine Tweaks your comments will be overwritten\n\n')
            parser.write(f, False)
            return value
        return parser.get('main', option, fallback="")


    def _fastest_mirror(self, enabled: bool|None = None):
        if enabled is not None:
            self.maxparallel.set_sensitive(enabled)
            return bool(self._global_cfg('fastestmirror', str(enabled)))
        res = self._global_cfg('fastestmirror') or "False"
        match res:
            case "True":
                self.maxparallel.set_sensitive(True)
                return True
            case "False":
                self.maxparallel.set_sensitive(False)
                return False
            case _:
                self.maxparallel.set_sensitive(False)
                print("dnf_repos: fastestmirror: unknown value: " + res)
                return False

    def on_row_activated(self, treeview, path: str, column):

        # print(f"row activated: {path}")
        # print(f"column activated: {column}")
        # print(f"from treeview: {treeview}")
        # print("row activated")
        # get the repo id of the activated row
        repo_id = self.treeview_model[path][0]
        assert (repo := YumRepo.find_from_id(repo_id))
        self.selected_row = repo
        # print(f"repo id: {repo_id}")
        # print(f"repo: {YumRepo.find_from_id(repo_id).__dict__}")
        self.update()

    def update(self):
        # update the options below
        self.repo_name_row.set_text(self.selected_row.name)
        self.baseurl_row.set_text(self.selected_row.baseurl)
        self.mirrorurl_row.set_text(self.selected_row.metalink)
        self.enabled_row.set_value(self.selected_row.enabled)

    def set_enabled(self, widget: Gtk.Switch, _: GObject.GType | None):
        # get active value
        print(widget.get_active())
        active = widget.get_active()
        # run operation as root
        self.selected_row.set_boolean(self.selected_row.id, "enabled", active)
        self.update()

    def set_mirrorurl(self, widget: Gtk.Entry):
        # get active value
        print(widget.get_text())
        # run operation as root
        self.selected_row.set_config(
            self.selected_row.id, "metalink", widget.get_text()
        )
        self.update()

    def set_baseurl(self, widget: Gtk.Entry):
        # get active value
        print(widget.get_text())
        # run operation as root
        self.selected_row.set_config(self.selected_row.id, "baseurl", widget.get_text())
        self.update()
