FROM ubuntu:22.04

ENV debian_frontend=noninteractive


RUN apt-get update && apt-get install -y \
    curl \
    libncurses5-dev \
    libncursesw5-dev \
    git \
    gcc \
    make \
    zlib1g-dev \
    libssl-dev \ 
    libffi-dev \ 
    libbz2-dev

RUN curl https://pyenv.run | bash

ENV HOME /root
ENV PYENV_ROOT $HOME/.pyenv
ENV PATH $PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

RUN pyenv install 3.7
RUN pyenv global 3.7

ENV PATH $HOME/.local/bin:$PATH
ENV TERM xterm-256color

RUN pip install --user pqcli

CMD ["pqcli"]