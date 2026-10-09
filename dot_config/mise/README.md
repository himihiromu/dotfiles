# mise tasks

This directory contains global mise tasks for the local `my-nix-package-control`
repository at `~/ghq/github.com/himihiromu/my-nix-package-control`. Tasks can be
run from any working directory after chezmoi applies this configuration.

| Command | What it does |
| --- | --- |
| `mise develop <environment>` | Starts `nix develop` for the named flake environment. |
| `mise home-manager switch` | Runs Home Manager against `#myHomeConfig`, including the local options input. |
| `mise nis-darwin switch` | Runs nix-darwin against `#mac-config`, including the local options input. |
| `mise nixos switch` | Runs `nixos-rebuild switch` against the local repository flake. |
| `mise nix update` | Runs `nix flake update` for the local repository. |
| `mise nix gc` | Runs `nix-store --gc`. |

The `home-manager`, `nis-darwin`, and `nixos` switch tasks use `sudo` where
required. `mise nix gc` removes unused paths from the Nix store.
