#!/usr/bin/env bash
ENV_NAME=$1;
VERSION=$(head -n 1 ../../VERSION)

echo -e "================"
echo -e "VEBA v${VERSION}"
echo -e "================"

# Check if environment file exists
FILE=../environments/${ENV_NAME}.yml
if [ -f "$FILE" ]; then
    NAME=$(echo $ENV_NAME | cut -f1 -d "_" | cut -c6-)
    TAG="veba/${NAME}:${VERSION}"
    echo -e "Creating Docker image ${TAG} for ${ENV_NAME}"
    docker build --build-arg ENV_NAME=${ENV_NAME} -t ${TAG} -f Dockerfile ../../
else 
    echo -e "$FILE does not exist."
fi
