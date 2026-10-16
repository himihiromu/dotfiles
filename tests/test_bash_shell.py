"""Isolated Readline integration tests; no real history, ghq repos or dotfiles apply."""
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import shlex
import shutil
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which('bash')


class Shell:
    def __init__(self, dependencies=True):
        self.tmp = tempfile.TemporaryDirectory(prefix='.bash-test-', dir=ROOT)
        self.home = Path(self.tmp.name)
        bin_dir = self.home / 'bin'
        bin_dir.mkdir()
        (bin_dir / 'sed').symlink_to(shutil.which('sed'))
        self.repo = self.home / 'repo with spaces; literal $name'
        self.repo.mkdir()
        if dependencies:
            for name, body in {
                'ghq': '[[ $* == "list --full-path" ]] || exit 9\n[[ ! -f $HOME/ghq-fail ]] || exit 1\nprintf "%s\\n" "$TEST_REPO"',
                'fzf': 'printf "%s\\n" "$@" > "$HOME/fzf-args"\nwhile IFS= read -r line; do printf "%s\\n" "$line"; done > "$HOME/fzf-input"\n[[ ! -f $HOME/cancel ]] || exit 130\n[[ ! -f $HOME/empty ]] || exit 0\nIFS= read -r selection < "$HOME/selection"\nprintf "%s\\n" "$selection"',
            }.items():
                script = bin_dir / name
                script.write_text(f'#!{BASH}\n{body}\n')
                script.chmod(0o755)
        rc = self.home / 'rc'
        rc.write_text(f'PATH={shlex.quote(str(bin_dir))}\nsource {shlex.quote(str(ROOT / "dot_bashrc"))}\n'
                      "PS1='TEST_PROMPT> '\nPS2='CONTINUE> '\n"
                      "HISTFILE=/dev/null\nPROMPT_COMMAND=\n"
                      "unalias ls 2>/dev/null\n"
                      "ls() { printf 'LS_ARGS:%s\\n' \"$*\"; }\n")
        self.pid, self.fd = pty.fork()
        if self.pid == 0:
            os.chdir(self.home)
            os.execve(BASH, [BASH, '--noprofile', '--rcfile', str(rc), '-i'], {
                'HOME': str(self.home), 'PATH': str(bin_dir), 'TERM': 'dumb',
                'TEST_REPO': str(self.repo), 'LC_ALL': 'C.UTF-8', 'INPUTRC': '/dev/null',
            })
        self.read_prompt()

    def read_prompt(self):
        data = b''
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if select.select([self.fd], [], [], .1)[0]:
                data += os.read(self.fd, 65536)
                if data.endswith(b'TEST_PROMPT> ') and not select.select([self.fd], [], [], .1)[0]:
                    return data.decode(errors='replace')
        raise AssertionError(f'No shell prompt: {data!r}')

    def run(self, text):
        os.write(self.fd, text.encode())
        return self.read_prompt()

    def select(self, value):
        (self.home / 'selection').write_text(value + '\n')

    def close(self):
        os.kill(self.pid, signal.SIGHUP)
        os.waitpid(self.pid, 0)
        os.close(self.fd)
        self.tmp.cleanup()


class BashErgonomics(unittest.TestCase):
    def setUp(self):
        self.shell = Shell()
        self.addCleanup(self.shell.close)

    def test_abbreviations_on_space_and_enter(self):
        for abbr, flags in [('la', '-a'), ('ll', '-l'), ('lal', '-al')]:
            self.assertIn(f'LS_ARGS:{flags} file', self.shell.run(abbr + ' file\r'))
            self.assertIn(f'LS_ARGS:{flags}', self.shell.run(abbr + '\r'))
        output = self.shell.run('history 8\n')
        self.assertIn('ls -al', output)

    def test_literal_arguments_and_cursor_suffix(self):
        self.assertIn('VALUE:ll', self.shell.run("printf 'VALUE:%s\\n' ll\r"))
        # Move left over the suffix: expansion must preserve the editable remainder.
        self.assertIn('LS_ARGS:-l file', self.shell.run('llfile' + '\x02' * 4 + ' \r'))
        self.assertIn('LS_ARGS:-a', self.shell.run('  la\r'))

    def test_history_selection_does_not_execute(self):
        self.shell.run("history -s 'printf HISTORY_SELECTED'\n")
        self.shell.select('printf HISTORY_SELECTED')
        self.assertIn('HISTORY_SELECTED', self.shell.run('HISTORY\x12\r'))
        self.assertIn('printf HISTORY_SELECTED', (self.shell.home / 'fzf-input').read_text())
        self.assertEqual((self.shell.home / 'fzf-args').read_text().splitlines(),
                         ['--tac', '--no-multi', '--query', 'HISTORY'])
        # Selected shell syntax is inserted, never evaluated by the widget itself.
        self.shell.select('printf EXECUTED > SHOULD_NOT_EXIST')
        self.shell.run('\x12\x18\x15\n')
        self.assertFalse((self.shell.home / 'SHOULD_NOT_EXIST').exists())

    def test_ghq_immediate_cd_and_clear(self):
        self.shell.select(str(self.shell.repo))
        output = self.shell.run('invalid_draft\x15pwd\r')
        self.assertIn(str(self.shell.repo), output)
        self.assertNotIn('command not found', output)
        self.assertEqual((self.shell.home / 'fzf-input').read_text().strip(), str(self.shell.repo))

    def test_cancel_empty_failure_preserve_input_and_directory(self):
        for marker in ['cancel', 'empty', 'ghq-fail']:
            with self.subTest(marker=marker):
                (self.shell.home / marker).touch()
                self.assertIn('KEPT', self.shell.run('printf KEPT\x15\r'))
                self.assertIn(str(self.shell.home), self.shell.run('pwd\r'))
                (self.shell.home / marker).unlink()
        self.shell.select(str(self.shell.home / 'missing'))
        self.assertIn('KEPT', self.shell.run('printf KEPT\x15\r'))
        (self.shell.home / 'cancel').touch()
        self.assertIn('HISTORY_KEPT', self.shell.run('printf HISTORY_KEPT\x12\r'))

    def test_original_kill_line_and_existing_alias(self):
        self.assertIn('CLEARED', self.shell.run('invalid\x18\x15printf CLEARED\r'))
        self.assertIn("alias l='ls -CF'", self.shell.run('alias l\r'))

    def test_unicode_input_and_history_cursor(self):
        self.assertIn('日本語 suffix', self.shell.run("printf '%s' '日本語 suffix'\r"))
        self.shell.select("printf '%s' '日本語'")
        self.assertIn('日本語追加', self.shell.run('\x12\x02追加\r'))

    def test_noninteractive_source_is_noop(self):
        result = subprocess.run(
            [BASH, '--noprofile', '--norc', '-c',
             'source "$1"; declare -F __bash_abbr_expand; printf "DONE"',
             'test', str(ROOT / 'dot_bashrc')],
            env={'HOME': str(self.shell.home), 'PATH': '/nonexistent'},
            capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, 'DONE')
        self.assertEqual(result.stderr, '')

    def test_missing_dependencies_leave_native_keys(self):
        other = Shell(dependencies=False)
        self.addCleanup(other.close)
        output = other.run('bind -p\n')
        self.assertIn('"\\C-u": unix-line-discard', output)
        self.assertIn('"\\C-r": reverse-search-history', output)
        self.assertIn('LS_ARGS:-l', other.run('ll\r'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
