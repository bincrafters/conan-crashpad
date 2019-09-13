#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update || brew update
    brew outdated pyenv || brew upgrade pyenv
    brew install pyenv-virtualenv
    brew install cmake || true

    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi

    # Google's depot_tools don't work well with new python versions. For now, we
    # will use -- the soon to be deprecated -- python 2.7 as a workaround.
    pyenv install 2.7.16
    pyenv virtualenv 2.7.16 conan
    pyenv rehash
    pyenv activate conan
fi

pip install conan --upgrade
pip install conan_package_tools bincrafters_package_tools

conan user
