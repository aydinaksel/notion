{
  description = "Notion weekly summary and TLDR scripts";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
  };

  outputs = { self, nixpkgs }:
    let
      systems = [ "aarch64-darwin" "x86_64-darwin" "aarch64-linux" "x86_64-linux" ];
      forAllSystems = nixpkgs.lib.genAttrs systems;

      ntnVersion = "0.15.0";
      ntnSources = {
        aarch64-darwin = {
          target = "aarch64-apple-darwin";
          hash = "sha256-VZz3UBU1/FUps3pNVbJvHqa5WrUm9nzE8LBNudeC1og=";
        };
        x86_64-darwin = {
          target = "x86_64-apple-darwin";
          hash = "sha256-GSRPZ4D6bMp1Am/skYkybtsYPpasuuPf+dTc6iWladw=";
        };
        x86_64-linux = {
          target = "x86_64-unknown-linux-musl";
          hash = "sha256-a/7Eq/pS06yPFXUyHxHsX/qJb37YnrSq20vofN1FG/Q=";
        };
        aarch64-linux = {
          target = "aarch64-unknown-linux-musl";
          hash = "sha256-4Wi/byIXgqFofLwjD0Ib39q1J5pGuhWjmtj8nyoDMGE=";
        };
      };
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
          ntnSource = ntnSources.${system};

          ntn = pkgs.stdenv.mkDerivation {
            pname = "ntn";
            version = ntnVersion;

            src = pkgs.fetchzip {
              url = "https://ntn.dev/releases/v${ntnVersion}/ntn-${ntnSource.target}.tar.gz";
              hash = ntnSource.hash;
            };

            phases = [ "installPhase" ];

            installPhase = ''
              mkdir -p $out/bin
              cp $src/ntn $out/bin/ntn
              chmod +x $out/bin/ntn
            '';
          };
        in
        {
          default = pkgs.mkShell {
            packages = [
              pkgs.python3
              ntn
            ];
          };
        }
      );
    };
}
