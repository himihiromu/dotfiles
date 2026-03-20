#!/bin/bash

# Nix のインストール
if [ ! -d /nix ]; then
  curl -fsSL https://install.determinate.systems/nix | sh -s -- install
fi
exec $SHELL -l
