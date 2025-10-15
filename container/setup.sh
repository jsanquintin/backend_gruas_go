#!/usr/bin/env bash

## ========== ##
##    Init    ##
## ========== ##

# Start podman socker and auto-update timer
if [ $(systemctl --user is-enabled podman.socket) == "disabled" ]; then
	systemctl --user enable --now podman.socket podman-auto-update.timer
fi

## ================== ##
##    Environments    ##
## ================== ##
APP_NAME="GruasGo"

## Rutas
ROOTLESS_PATH="${HOME}/.config/containers"

# container setup for rootless
if [ ! -d "${ROOTLESS_PATH}" ]; then
	rsync -avx --exclude="*storage.conf*" --ignore-existing /usr/share/containers "${ROOTLESS_PATH}"
	printf '[storage]\ndriver = "btrfs"\n' >"${ROOTLESS_PATH}"/storage.conf
fi

## ============= ##
##    Volumes    ##
## ============= ##
folders=(
	"misc"
	"profile_pics"
	"ride_receipts"
)
paths="${PWD}/.volume"
for d in "${folders[@]}"; do
	if [ ! -d "${paths}/${d}" ]; then
		mkdir -p "${paths}/${d}"
	fi
	podman volume create \
		-o type=none \
		-o device="${paths}/${d}" \
		-o=o=bind \
		"${d%%/*}-${d#*/}"
done

podman build --rm \
	--force-rm \
	--no-cache \
	--ignorefile container/.containerignore \
	-t gruasgo -f container/containerfile .

podman run -d \
	-p 80:8000 \
	--name gruasgo \
	-v misc:/app/static/misc \
	-v profile_pics:/app/static/profile_pics \
	-v ride_receipts:/app/static/ride_receipts
localhost/gruasgo:latest

podman generate systemd --new -n gruasgo | SYSTEMD_EDITOR=tee systemctl --user edit --full --force gruasgo.service
