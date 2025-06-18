FROM debian:bookworm-slim

ARG PASSWORD_USERNAME=scrapli-pw
ARG PASSWORD_PASSWORD=scrapli-123-pw
ARG KEY_USERNAME=scrapli-key

RUN mkdir /var/run/sshd

RUN apt-get update -yq && \
    apt-get install -yq \
    --no-install-recommends \
    ca-certificates \
    build-essential \
    openssh-server

RUN useradd -m -s /bin/bash ${PASSWORD_USERNAME} && \
    echo "${PASSWORD_USERNAME}:${PASSWORD_PASSWORD}" | chpasswd

RUN useradd -m -s /bin/bash ${KEY_USERNAME}

COPY scrapli-jumper-key.pub /home/${KEY_USERNAME}/.ssh/authorized_keys
RUN chown -R ${KEY_USERNAME}:${KEY_USERNAME} /home/${KEY_USERNAME}/.ssh && \
    chmod 700 /home/${KEY_USERNAME}/.ssh && \
    chmod 600 /home/${KEY_USERNAME}/.ssh/authorized_keys

COPY sshd_config /etc/ssh/sshd_config

EXPOSE 22

CMD ["/usr/sbin/sshd", "-D"]
