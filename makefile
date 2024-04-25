IMG_NAME := progressquest-cli
TAG := latest

.PHONY: build run

build:
	docker build -t $(IMG_NAME):$(TAG) --file Containerfile .

run:
	docker run --rm -it $(IMG_NAME):$(TAG)
