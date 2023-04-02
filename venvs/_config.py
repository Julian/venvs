from functools import lru_cache
import json
import os
import subprocess
import sys

from pyrsistent import freeze, pmap, pvector, thaw
import attr
import filesystems.exceptions
import tomlkit


class DuplicatedLinks(Exception):
    pass


def _empty():
    table = tomlkit.table()
    table["bundle"] = tomlkit.table()
    table["virtualenv"] = tomlkit.table()
    return table


@attr.s(frozen=True)
class ConfiguredVirtualEnv:
    """
    A virtual environment defined within a config file section.
    """

    name = attr.ib()
    python = attr.ib(default=sys.executable)
    install = attr.ib(default=pvector())
    requirements = attr.ib(default=pvector())
    link = attr.ib(default=pmap())
    link_module = attr.ib(default=pmap())
    post_commands = attr.ib(default=pvector())

    @classmethod
    def from_dict(cls, name, config_dict, bundles):
        # tomlkit's data structures are broken in at least one way,
        # see sdipater/tomlkit#49, but I don't trust them not to be
        # broken in other ways given that they inherit from dict
        requirements = _interpolated(config_dict.get("requirements", []))
        install = list(_interpolated(config_dict.get("install", [])))

        for bundle_name in config_dict.get("install-bundle", []):
            bundle = bundles[bundle_name]
            for each in bundle:
                if each not in install:
                    install.append(each)

        kwargs = dict(
            install=pvector(install),
            requirements=pvector(requirements),
            python=config_dict.get("python", sys.executable),
            post_commands=freeze(config_dict.get("post-commands", [])),
        )
        for section in "link", "link-module":
            links = (
                each.partition(":") for each in config_dict.get(section, [])
            )
            # target -> source, since it's target names that must be unique
            kwargs[section.replace("-", "_")] = pmap(
                (to or name, name) for name, _, to in links
            )
        return cls(name=name, **kwargs)

    def save(self, filesystem, virtualenv):
        filesystem.set_contents(
            virtualenv.path / "installed.json",
            mode="t",
            contents=json.dumps(
                self._serializable(),
                ensure_ascii=False,
                indent=2,
            ),
        )

    def matches_existing(self, virtualenv, filesystem):
        try:
            existing = json.loads(
                filesystem.get_contents(virtualenv.path / "installed.json"),
            )
        except (ValueError, filesystems.exceptions.FileNotFound):
            return False
        return existing == self._serializable()

    def _serializable(self):
        return {
            "virtualenv": thaw(pmap(attr.asdict(self))),
            "sys.version": _version_of(self.python),
        }


@attr.s(eq=False, frozen=True)
class Config:
    """
    A converge configuration file.
    """

    _contents = attr.ib(factory=_empty)

    @classmethod
    def from_string(cls, string):
        document = tomlkit.loads(string)
        # tomlkit's setdefault is broken, see sdipater/tomlkit#49
        for each in "virtualenv", "bundle":
            if each not in document:
                document[each] = tomlkit.table()
        _check_for_duplicated_links(document["virtualenv"].values())
        return cls(contents=document)

    @classmethod
    def from_locator(cls, locator, filesystem):
        contents = filesystem.get_contents(
            locator.root.descendant("virtualenvs.toml"),
            mode="t",
        )
        return cls.from_string(contents)

    def __iter__(self):
        return (
            ConfiguredVirtualEnv.from_dict(
                name=name,
                config_dict=config,
                bundles=self._contents["bundle"],
            )
            for name, config in self._contents["virtualenv"].items()
        )

    def __eq__(self, other):
        """
        Compare the effective configuration dictated by the 2 configs.
        """
        if self.__class__ is not other.__class__:
            return NotImplemented
        return all(a == b for a, b in zip(self, other))

    def __ne__(self, other):
        return not self == other

    def __len__(self):
        return len(self._contents["virtualenv"])

    def add(
        self,
        name,
        install=(),
        requirements=(),
        link=(),
        link_module=(),
    ):
        # tomlkit's table.copy is broken, see sdipater/tomlkit#65
        contents = tomlkit.parse(self._contents.as_string())
        contents["virtualenv"].add(name, tomlkit.table())
        contents["virtualenv"][name].update(
            {
                "install": list(install),
                "requirements": list(requirements),
                "link": sorted(set(link)),
                "link-module": sorted(set(link_module)),
            },
        )
        return attr.evolve(self, contents=contents)


def _interpolated(iterable):
    return (os.path.expandvars(os.path.expanduser(each)) for each in iterable)


def add_virtualenv(filesystem, locator, installs, links, name):
    try:
        config = Config.from_locator(filesystem=filesystem, locator=locator)
    except filesystems.exceptions.FileNotFound:
        config = Config()
    new = config.add(name, install=installs, link=links)
    filesystem.set_contents(
        locator.root.descendant("virtualenvs.toml"),
        tomlkit.dumps(new._contents),
        mode="t",
    )


def _check_for_duplicated_links(sections):
    seen, duplicated = set(), set()
    for each in sections:
        for link in each.get("link", []) + each.get("link-module", []):
            name, _, to = link.partition(":")
            to = to or name
            if to in seen:
                duplicated.add(to)
            seen.add(to)
    if duplicated:
        raise DuplicatedLinks(duplicated)


@lru_cache
def _version_of(python):
    return subprocess.check_output(
        [python, "--version"],
        stderr=subprocess.STDOUT,
    ).decode("ascii")
