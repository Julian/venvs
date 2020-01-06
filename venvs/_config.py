import os
import sys

from pyrsistent import pset
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


@attr.s(eq=False, frozen=True)
class Config(object):
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
        for name, config in self._contents["virtualenv"].items():
            yield name, self._effective_config(config)

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
                "install": sorted(set(install)),
                "requirements": sorted(set(requirements)),
                "link": sorted(set(link)),
                "link-module": sorted(set(link_module)),
            },
        )
        return attr.evolve(self, contents=contents)

    def _effective_config(self, config):
        # tomlkit's data structures are broken in at least one way,
        # see sdipater/tomlkit#49, but I don't trust them not to be
        # broken in other ways given that they inherit from dict
        effective = {
            "install": pset(_interpolated(as_strings(
                config.get("install", []),
            ))),
            "requirements": pset(
                _interpolated(config.get("requirements", [])),
            ),
            "link": pset(as_strings(config.get("link", []))),
            "link-module": pset(config.get("link-module", [])),
            "python": config.get("python", sys.executable),
        }
        for bundle in config.get("install-bundle", []):
            effective["install"] = effective["install"].update(
                self._contents["bundle"][bundle],
            )
        return effective


def as_strings(iterable):
    return (str(each) for each in iterable)


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
