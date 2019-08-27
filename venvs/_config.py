import filesystems.exceptions
import tomlkit


class DuplicatedLinks(Exception):
    pass


def load(filesystem, locator):
    contents = filesystem.get_contents(
        locator.root.descendant("virtualenvs.toml"),
        mode="t",
    )
    config = tomlkit.loads(contents)
    _check_for_duplicated_links(config.get("virtualenv", {}).values())
    return config


def dump(config, filesystem, locator):
    try:
        filesystem.create_directory(locator.root)
    except filesystems.exceptions.FileExists:
        pass

    filesystem.set_contents(
        locator.root.descendant("virtualenvs.toml"),
        tomlkit.dumps(config),
        mode="t",
    )


def add_virtualenv(filesystem, locator, installs, links, name):
    try:
        contents = load(filesystem=filesystem, locator=locator)
    except filesystems.exceptions.FileNotFound:
        contents = tomlkit.table()
        contents.add("virtualenv", {})
    if "virtualenv" not in contents:
        contents = tomlkit.table()
        contents.add("virtualenv", {})

    contents["virtualenv"].add(
        name, {"install": list(installs), "link": list(links)}
    )
    dump(contents, filesystem=filesystem, locator=locator)


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
