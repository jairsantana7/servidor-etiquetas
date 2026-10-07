.DEFAULT_GOAL := help

ifeq ($(OS),Windows_NT)
PYTHON ?= python
VENV_PYTHON := .venv/Scripts/python.exe
else
PYTHON ?= python3.12
VENV_PYTHON := .venv/bin/python
endif

# Ex.: make start ARGS="--simulate --port 8081 --no-browser"
ARGS ?=

.PHONY: help install start build build-macos build-windows build-linux test venv

help:
	@"$(PYTHON)" -c "print('make install       Instala as dependencias\nmake start         Inicia o servidor e abre o navegador\nmake build         Gera o pacote do sistema atual\nmake build-macos   Gera .app, .dmg e .zip no macOS\nmake build-windows Gera .exe em .zip no Windows\nmake build-linux   Gera executavel em .tar.gz no Linux\nmake test          Executa os testes\n\nOpcoes: PYTHON=python3 e ARGS=\"--simulate --port 8081\"')"

venv: .venv/pyvenv.cfg

.venv/pyvenv.cfg:
	"$(PYTHON)" -m venv .venv

install: venv
	"$(VENV_PYTHON)" packaging/build.py --install --prepare-only

start: install
	"$(VENV_PYTHON)" launcher.py $(ARGS)

build: venv
	"$(VENV_PYTHON)" packaging/build.py --install

build-macos:
	@"$(PYTHON)" -c "import platform,sys; sys.exit(0 if platform.system() == 'Darwin' else 'Execute make build-macos em um Mac; nao ha compilacao cruzada.')"
	$(MAKE) build

build-windows:
	@"$(PYTHON)" -c "import platform,sys; sys.exit(0 if platform.system() == 'Windows' else 'Execute make build-windows no Windows; nao ha compilacao cruzada.')"
	$(MAKE) build

build-linux:
	@"$(PYTHON)" -c "import platform,sys; sys.exit(0 if platform.system() == 'Linux' else 'Execute make build-linux no Linux; nao ha compilacao cruzada.')"
	$(MAKE) build

test: install
	"$(VENV_PYTHON)" -m unittest discover -s tests -v
