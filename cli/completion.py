from __future__ import annotations

import sys


def _generate_bash_completion() -> str:
    return '''_nova_completions() {
    local cur prev commands
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="health chat execute workflow scheduler memory goals tasks agents plugins models tools observability deployment version config"
    if [[ ${cur} == -* ]]; then
        COMPREPLY=( $(compgen -W "--base-url --api-key --token --json --help -h" -- ${cur}) )
    elif [[ ${prev} == "nova" ]]; then
        COMPREPLY=( $(compgen -W "${commands}" -- ${cur}) )
    fi
    return 0
}
complete -F _nova_completions nova
'''


def _generate_zsh_completion() -> str:
    return '''#compdef nova

_nova() {
    _arguments \
        '1:command:(health chat execute workflow scheduler memory goals tasks agents plugins models tools observability deployment version config)' \
        '*::arg:->args'
}

_nova "$@"
'''


def _generate_powershell_completion() -> str:
    return '''Register-ArgumentCompleter -Native -CommandName nova -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)
    $commands = @('health','chat','execute','workflow','scheduler','memory','goals','tasks','agents','plugins','models','tools','observability','deployment','version','config')
    $commands | Where-Object { $_ -like "$wordToComplete*" } | ForEach-Object {
        [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_)
    }
}
'''


def install_completion(shell: str | None = None) -> None:
    if shell == "bash" or (not shell and sys.platform != "win32"):
        print(_generate_bash_completion())
    elif shell == "zsh":
        print(_generate_zsh_completion())
    elif shell == "powershell":
        print(_generate_powershell_completion())
    else:
        print("Supported shells: bash, zsh, powershell")
        print("Usage: nova completion [bash|zsh|powershell]")
