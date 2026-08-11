{
  description = "Interactive chezmoi bootstrap for himihiromu's dotfiles";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
        "x86_64-darwin"
        "aarch64-darwin"
      ];
      forAllSystems = nixpkgs.lib.genAttrs systems;
    in
    {
      formatter = forAllSystems (system: nixpkgs.legacyPackages.${system}.nixfmt-tree);

      packages = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        rec {
          init = pkgs.writeShellApplication {
            name = "dotfiles-init";
            runtimeInputs = [
              pkgs.chezmoi
              pkgs.git
            ];
            text = ''
              exec chezmoi init --apply himihiromu/dotfiles "$@"
            '';
          };
          default = init;
        }
      );

      apps = forAllSystems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          init = self.packages.${system}.init;
        in
        {
          init = {
            type = "app";
            program = pkgs.lib.getExe init;
          };
          default = {
            type = "app";
            program = pkgs.lib.getExe init;
          };
        }
      );
    };
}
