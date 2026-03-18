nix run nixpkgs#home-manager -- switch --flake github:himihiromu/my-nix-package-control#myHomeConfig \
  --override-input local-options path:$HOME/.config/nix/local-input/
