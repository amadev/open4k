#!/usr/bin/env bash

set -o pipefail
set -o errexit
set -o xtrace

function test_create_instance () {
    kubectl apply -f examples/devstack-instance.yaml
    while true; do
        status=$(kubectl get instance open4k-vm1 -o json | jq '.status.object.status')
        if [ "$status" = "ACTIVE" ]; then
            break;
        fi
    done
    kubectl delete -f examples/devstack-instance.yaml
}
