#!/bin/bash
set -euo pipefail

action=${1:?Missing action}
support=${2:?Missing application support directory}
resources=$(cd -- "$(dirname -- "$0")" && pwd)

docker_app=/Applications/Docker.app
if [[ ! -d "$docker_app" ]]; then
    docker_app="$HOME/Applications/Docker.app"
fi
docker="$docker_app/Contents/Resources/bin/docker"
compose="$docker_app/Contents/Resources/cli-plugins/docker-compose"
if [[ ! -x "$docker" || ! -x "$compose" ]]; then
    echo 'Install Docker Desktop for Mac, open it to finish setup, then retry Medora.' >&2
    exit 12
fi

export DOCKER_CONTEXT=desktop-linux
unset DOCKER_HOST
config="$support/settings.env"
stack=("$compose" --project-name medora-desktop --file "$resources/compose.yml"
    --env-file "$resources/images.env" --env-file "$config")

docker_ready() {
    [[ -n $("$docker" version --format '{{.Server.Version}}' 2>/dev/null) ]]
}

case "$action" in
    start)
        if ! docker_ready; then
            echo 'Opening Docker Desktop…'
            /usr/bin/open -g "$docker_app"
            deadline=$((SECONDS + 150))
            until docker_ready; do
                if (( SECONDS >= deadline )); then
                    echo 'Docker Desktop did not become ready. Check Docker Desktop for a setup prompt.' >&2
                    exit 13
                fi
                sleep 2
            done
        fi

        umask 077
        mkdir -p "$support"
        if [[ ! -f "$config" ]]; then
            temporary_config=$(mktemp "$support/settings.XXXXXXXX")
            trap 'rm -f -- "$temporary_config"' EXIT
            printf 'MEDORA_DATABASE_PASSWORD=%s\nMEDORA_SECRET_KEY=%s\n' \
                "$(/usr/bin/openssl rand -hex 32)" "$(/usr/bin/openssl rand -hex 32)" > "$temporary_config"
            mv -- "$temporary_config" "$config"
        fi

        image_list=$("${stack[@]}" config --images)
        while IFS= read -r image; do
            if ! "$docker" image inspect "$image" >/dev/null 2>&1; then
                echo 'Loading the bundled Medora images…'
                "$docker" image load --input "$resources/images.tar.gz"
                break
            fi
        done <<< "$image_list"

        echo 'Starting the Medora application and database…'
        if ! "${stack[@]}" up --detach --no-build --pull never --wait --wait-timeout 75; then
            "${stack[@]}" logs --tail 40 >&2 || true
            exit 14
        fi
        /usr/bin/curl --fail --silent --show-error --max-time 5 --noproxy '*' \
            http://127.0.0.1:38180/api/ping
        ;;
    stop)
        if [[ -f "$config" ]] && docker_ready; then
            "${stack[@]}" stop --timeout 8
        fi
        ;;
    *)
        echo "Unknown Medora action: $action" >&2
        exit 2
        ;;
esac
