{pkgs}: {
  deps = [
    pkgs.lsof
    pkgs.nano
    pkgs.mailutils
    pkgs.postgresql
    pkgs.openssl
  ];
}
