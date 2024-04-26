IMG_NAME := progressquest-cli
TAG := latest

.PHONY: build run

build:
	docker build -t $(IMG_NAME):$(TAG) --file Containerfile .

run:
	mkdir ./saves
	docker run --rm -it -v ./saves:/home/quester/.config/pqcli $(IMG_NAME):$(TAG)
