#!/bin/bash

# Nix のインストール
if [ ! -d /nix ]; then
  curl -fsSL https://install.determinate.systems/nix | sh -s -- install
  . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh
fi

