FROM python:3.11

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade colorlog black pylint python-language-server
RUN python -m pip install --upgrade homeassistant
RUN cd && mkdir -p /config/custom_components


WORKDIR /workspace

# Set the default shell to bash instead of sh
ENV SHELL /bin/bash
