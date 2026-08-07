from __future__ import annotations

import subprocess
import sys
import typing

import pytest

from multical.app.multical import Multical


COMMANDS = [
    "calibrate",
    "intrinsic",
    "boards",
    "vis",
    "rectify",
    "world",
    "worldmulti",
    "observe",
    "triangulate",
    "evaluate3d",
]


def test_cli_command_annotations_backward_compatible():
    command_type = typing.get_origin(Multical.__annotations__["command"])
    assert command_type is typing.Union

    command_members = typing.get_args(Multical.__annotations__["command"])
    command_names = {cmd.__name__.lower() for cmd in command_members}
    expected = set(COMMANDS)
    assert expected.issubset(command_names)


def test_cli_help_invocation():
    result = subprocess.run(
        [sys.executable, "-m", "multical.app.multical", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "multical" in output
    assert "intrinsic" in output
    assert "calibrate" in output
    assert "world" in output


@pytest.mark.parametrize("command", COMMANDS)
def test_subcommand_help_invocation(command):
    result = subprocess.run(
        [sys.executable, "-m", "multical.app.multical", command, "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "usage:" in (result.stdout + result.stderr)
