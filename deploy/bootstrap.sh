#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID}" -ne 0 ]]; then echo 'Run as root'; exit 1; fi
. /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 ]] || { echo 'Expected Ubuntu 24.04'; exit 1; }
sshd -T | awk '$1 == "port" {print $2}' | grep -qx 30222 || { echo 'SSH port 30222 must be active before firewall changes'; exit 1; }
apt-get update
apt-get install -y ca-certificates curl ufw gnupg
install -m 0755 -d /etc/apt/keyrings
curl --fail --silent --show-error --location https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$(dpkg --print-architecture)" "$VERSION_CODENAME" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
ufw allow 30222/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable
install -d -m 0755 /opt/greenmine
# A small runtime host may need swap during builds; do not replace existing swap.
if ! swapon --noheadings | grep -q .; then
    if [[ ! -e /swapfile ]]; then
        fallocate -l 2G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        grep -q '^/swapfile ' /etc/fstab || printf '/swapfile none swap sw 0 0\n' >> /etc/fstab
    fi
fi
docker version --format '{{.Server.Version}}'
docker compose version
ufw status
