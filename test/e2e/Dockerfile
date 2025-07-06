FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# Simplified approach - test the script logic with Docker client
RUN apt-get update || true && \
    apt-get install -y --no-install-recommends \
       bash curl wget sudo ca-certificates gnupg lsb-release \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update || true \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* || true

# Create a test user
ARG DOCKER_GID=999
RUN groupadd -g ${DOCKER_GID} docker && \
    useradd -m -s /bin/bash testuser && \
    usermod -aG sudo testuser && \
    usermod -aG docker testuser && \
    echo "testuser ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

WORKDIR /workspace
COPY . /workspace
USER testuser
CMD ["/bin/bash"]
