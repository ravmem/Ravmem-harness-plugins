# RavMem for Antigravity

```
python3 antigravity/scripts/install_to_project.py /path/to/project    # project: .agents/ + GEMINI.md
python3 antigravity/scripts/install_to_project.py --global             # token in ~/.gemini/config/mcp_config.json
```

Project mode writes `.agents/mcp_config.json` (`serverUrl` + headers), rules, skills and scripts, and merges the
RavMem block into `GEMINI.md`. The MCP config does not read environment variables, so project mode leaves a
`YOUR_RAVMEM_TOKEN` placeholder: replace it and keep that file out of git, or use `--global`, which writes the real
token into your private user config (mode 600).

## Install the server

The `ravmem-setup` skill (user-invoked) installs and activates the RavMem server with Docker; run `python3 .agents/scripts/setup_stack.py` in a terminal so the license key is typed privately. See the repository README, "Installing the server".
