#!/bin/bash
set -e

echo "=== Installing build dependencies ==="
apt-get update -qq
apt-get install -y -qq \
  git zip unzip python3-pip python3-setuptools \
  build-essential ccache libffi-dev libssl-dev \
  python3-dev openjdk-17-jdk cmake libgcc-s1 patchelf

echo "=== Installing Buildozer + Cython ==="
pip3 install --quiet --upgrade pip
pip3 install --quiet buildozer cython

echo "=== Preparing Build Directory ==="
mkdir -p /app
cp -r /src/* /app/
cd /app

echo "=== Building APK ==="
export HOME=/root
echo y | buildozer android debug

echo "=== Copying output APK to Windows host ==="
mkdir -p /src/bin
cp -r /app/bin/* /src/bin/

echo "SUCCESS! LocalConvert.apk created in bin/ directory."
ls -l /src/bin/*.apk
