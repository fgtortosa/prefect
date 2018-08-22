import os
import pytest
import subprocess

from prefect import Flow
from prefect.engine import signals
from prefect.tasks.core.shell import ShellTask


def test_shell_initializes_and_runs_basic_cmd():
    with Flow() as f:
        task = ShellTask()(command="echo -n 'hello world'")
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert out.result[task].result == b"hello world"


@pytest.mark.skipif(
    subprocess.check_output(["which", "zsh"]) == b"", reason="zsh not installed."
)
def test_shell_runs_other_shells():
    with Flow() as f:
        task = ShellTask(shell="zsh")(command="echo -n $ZSH_NAME")
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert out.result[task].result == b"zsh"


def test_shell_inherits_env():
    with Flow() as f:
        task = ShellTask()(command="echo -n $MYTESTVAR")
    os.environ["MYTESTVAR"] = "42"
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert out.result[task].result == b"42"


def test_shell_task_accepts_env():
    with Flow() as f:
        task = ShellTask()(command="echo -n $MYTESTVAR", env=dict(MYTESTVAR="test"))
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert out.result[task].result == b"test"


def test_shell_task_doesnt_inherit_if_env_is_provided():
    with Flow() as f:
        task = ShellTask()(command="echo -n $HOME", env=dict(MYTESTVAR="test"))
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert out.result[task].result == b""


def test_shell_returns_stderr_as_well():
    with Flow() as f:
        task = ShellTask()(command="ls surely_a_dir_that_doesnt_exist || exit 0")
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    assert "No such file or directory" in out.result[task].result.decode()


def test_shell_initializes_and_runs_multiline_cmd():
    cmd = """
    for line in $(printenv)
    do
        echo "${line#*=}"
    done
    """
    with Flow() as f:
        task = ShellTask()(command=cmd, env={key: "test" for key in "abcdefgh"})
    out = f.run(return_tasks=[task])
    assert out.is_successful()
    lines = out.result[task].result.decode().split("\n")
    test_lines = [l for l in lines if l == "test"]
    assert len(test_lines) == 8


def test_shell_task_raises_fail_if_cmd_fails():
    with Flow() as f:
        task = ShellTask()(command="ls surely_a_dir_that_doesnt_exist")
    out = f.run(return_tasks=[task])
    assert out.is_failed()
    assert "Command failed with exit code" in str(out.result[task].message)