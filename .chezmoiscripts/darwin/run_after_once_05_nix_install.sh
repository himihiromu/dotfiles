#!/bin/zsh

# home-manager のインスコ
nix run nixpkgs#home-manager -- switch --flake github:himihiromu/my-nix-package-control#myHomeConfig --show-trace \
  --override-input local-options path:$HOME/.config/nix/local-input/default.nix

# nix-darwin のインスコ
sudo nix run nix-darwin -- switch --flake github:himihiromu/my-nix-package-control#mac-config \
  --override-input local-options path:$HOME/.config/nix/local-input/default.nix
