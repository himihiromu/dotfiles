#!/usr/bin/env bash

set -euo pipefail

nix_flake="github:himihiromu/my-nix-package-control"
local_options="path:$HOME/.config/nix/local-input/default.nix"

distribution_id=""
if [ -r /etc/os-release ]; then
  distribution_id="$(. /etc/os-release && printf '%s' "${ID:-}")"
fi

if [ "$distribution_id" = "nixos" ]; then
  sudo nixos-rebuild switch --flake "$nix_flake#nixos" \
    --override-input local-options "$local_options"
else
  nix run nixpkgs#home-manager -- switch --flake "$nix_flake#myHomeConfig" --show-trace \
    --override-input local-options "$local_options"
fi
