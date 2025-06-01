.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

fmt: ## Run formatters
	python -m isort launcher/ netopeer/
	python -m black launcher/ netopeer/

lint: ## Run linters
	python -m ruff check

build-netopeer-server: ## Builds the netopeer server image
	docker build \
		-f netopeer/Dockerfile \
		-t ghcr.io/scrapli/scrapli_clab/netopeer:dev-latest \
		netopeer

build-launcher: ## Builds the clab launcher image
	docker build \
		-f launcher/Dockerfile \
		-t ghcr.io/scrapli/scrapli_clab/launcher:dev-latest \
		launcher

build: build-netopeer-server build-launcher ## build both netopeer and the launcher

run: ## Runs the clab launcher
	rm -r .clab/*
	docker run \
		--rm \
		--name clab-launcher \
		--privileged \
		--pid=host \
		--stop-signal=SIGINT \
		-v /var/run/docker.sock:/var/run/docker.sock \
		-v /run/netns:/run/netns \
		-v "$$(pwd):$$(pwd)" \
		-e "WORKDIR=$$(pwd)/.clab" \
		-e "HOST_ARCH=$$(uname -m)" \
		ghcr.io/scrapli/scrapli_clab/launcher:dev-latest
