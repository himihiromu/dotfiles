#!/bin/bash

nix run nixpkgs#home-manager -- switch --flake github:himihiromu/my-nix-package-control#myHomeConfig --show-trace \
  --override-input local-options path:$HOME/.config/nix/local-input/default.nix
