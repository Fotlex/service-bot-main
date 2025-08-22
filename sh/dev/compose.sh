#!/bin/bash
docker compose -f .docker/docker-compose.dev.yaml --env-file=.env up
