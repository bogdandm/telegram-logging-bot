FROM python:3.6
MAINTAINER Bogdan Kalashnikov <bogdan.dm1995@yandex.ru>
ENV TERM=xterm

RUN pip install git+https://github.com/bogdandm/telegram-logging-bot.git --upgrade # v0.01
ADD config_docker.json /tmp/config.json
ENV CONFIG_PATH=/tmp/config.json
