{ pkgs ? import <nixpkgs> {} }:

with pkgs;
let
  pypkgs = pypkgs: with pypkgs; [
    pyqt5
    requests
    python-dateutil
  ];
  pyWpkgs = python3.withPackages pypkgs;
in
qt5.mkDerivation {
  name = "nix-shell";
  phases = [ "nobuildPhase" ];
  nobuildPhase = ''
    echo
    echo "This derivation is not meant to be built, aborting";
    echo
    exit 1
  '';

  QT_PLUGIN_PATH = qt515.qtbase.outPath + "/" + qt515.qtbase.qtPluginPrefix;

  buildInputs = [
    qt5.qtbase
    pyWpkgs

    # keep this line if you use bash
    bashInteractive
  ];
}
