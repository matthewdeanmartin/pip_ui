Defaults to . but...

usage: python -m build [-h] [--version] [--quiet | --verbose] [--outdir PATH]

                       [--sdist] [--wheel] [--metadata]
                       [--config-setting KEY[=VALUE] |
                       --config-json JSON_STRING] [--installer {pip,uv} |
                       --no-isolation] [--dependency-constraints-txt PATH]
                       [--skip-dependency-check]
                       [srcdir]
python -m build: error: unrecognized arguments: .

[Exited with code 2 in 0.20s]

venv custom destination of .blerg (instead of .venv)

directory 'C:\\Users\\matth\\AppData\\Local\\pypa\\virtualenv' into itself 'C:\\Users\\matth\\AppData\\Local\\pypa\\virtualenv\\Cache'."), using old location
find interpreter for spec PythonSpec(path=C:\github\pip_ui\.venv\Scripts\python.exe)
proposed PythonInfo(spec=CPython3.13.3.final.0-64-x86_64, system=C:\Users\matth\AppData\Roaming\uv\python\cpython-3.13-windows-x86_64-none\python.exe, exe=C:\github\pip_ui\.venv\Scripts\python.exe, platform=win32, version='3.13.3 (main, May 30 2025, 05:37:00) [MSC v.1943 64 bit (AMD64)]', encoding_fs_io=utf-8-utf-8)
usage: virtualenv [--version] [--with-traceback] [-v | -q]
                  [--read-only-app-data] [--app-data APP_DATA]
                  [--reset-app-data] [--upgrade-embed-wheels]
                  [--discovery {builtin}] [-p py] [--try-first-with py_exe]
                  [--creator {builtin,cpython3-win,venv}]
                  [--seeder {app-data,pip}] [--no-seed]
                  [--activators comma_sep_list] [--clear] [--no-vcs-ignore]
                  [--system-site-packages] [--copies] [--no-download |
                  --download] [--extra-search-dir d [d ...]] [--pip version]
                  [--setuptools version] [--no-pip] [--no-setuptools]
                  [--no-periodic-update] [--symlink-app-data] [--prompt prompt]
                  [-h]
                  dest
virtualenv: error: unrecognized arguments: .blerg
SystemExit: 2

[Exited with code 2 in 0.54s]

pip audit with defaults (blank requirements file) Weird we're not using pip-audit? or is this pip-audit no longer standalone?

DEBUG:pip_audit._cli:parsed arguments: Namespace(local=False, requirements=None, project_path=WindowsPath('audit'), locked=False, format=<OutputFormatChoice.Columns: 'columns'>, vulnerability_service=<VulnerabilityServiceChoice.Pypi: 'pypi'>, osv_url='https://api.osv.dev/v1/query', dry_run=False, strict=False, desc=<VulnerabilityDescriptionChoice.Auto: 'auto'>, aliases=<VulnerabilityAliasChoice.Auto: 'auto'>, cache_dir=None, progress_spinner=<ProgressSpinnerChoice.On: 'on'>, timeout=15, paths=[], verbose=1, fix=False, require_hashes=False, index_url=None, extra_index_urls=[], skip_editable=False, no_deps=False, output=WindowsPath('stdout'), ignore_vulns=[], disable_pip=False)
ERROR:pip_audit._cli:couldn't find a supported project file in audit

[Exited with code 1 in 1.74s]

This is because it is picking up globals -v? Cross tool globals would need to adapt for each. Maybe feature for roadmap.

Usage: hatch build [OPTIONS] [LOCATION]
Try 'hatch build --help' for help.

Error: No such option '-v'.

[Exited with code 2 in 0.29s]


