{ pkgs ? import <nixpkgs> {} }:
let
  apted = { lib, buildPythonPackage, fetchPypi }:
    buildPythonPackage rec {
      pname = "apted";
      version = "1.0.3";
      src = fetchPypi {
        inherit pname version;
        sha256 = "vvpRgeLURX+ojlSZWoJgTuBIuy+8eB6pfY4YVrRxXOk=";
      };
      doCheck = false;
    };

  python = pkgs.python3.withPackages (p: with p; [
    JPype1
    (p.callPackage apted {})
  ]);

in
pkgs.mkShell {
  buildInputs = [
    python
    pkgs.jdk8
  ];
}