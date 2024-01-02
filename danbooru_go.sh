nix-shell -p 'python39.withPackages(ps: with ps; [ discordpy toml ])' --run "python bot.py"
