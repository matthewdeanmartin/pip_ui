CRITICAL
- Global Options is just too honking big. Change to a button that opens a window where these are set globally and then in the command panel, show only the things that are set different from blank/default as labels.

IMPORTANT 
- Top bar should be a dropdown list of detected requirements.txt files (and does pip support pyproject.toml?)
  - When requirements file is selected all commands should get that requiremetns file.
  - User can still change it at the command panel level.
  - search only current directory
- It should also look for other .txt files and do heuristics to decide if they look like requriements.txt files.
- Automatically run config list, config debug, list with default args (and any other info-only commands that are based on 
info like, current directory or active requirements file)
- Command to self upgrade.
- Colorful message when there is a upgrade available.

NICE
- Default to notepad.exe on widows if editor isn't set.
- Sub command help needs to be available on all command pages with a subcommand.
  - Command Help tab I guess, next ot Command Info.
- When selecting a new command on side tree, clear the combined, stdout, stderr, etc.
- Reasonable defaults
  - default destination folder is ./downloads  for artifacts/download
  - default wheel directory is ./dist
