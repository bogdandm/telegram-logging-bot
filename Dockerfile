FROM python:3.6
MAINTAINER Bogdan Kalashnikov <bogdan.dm1995@yandex.ru>
ENV TERM=xterm
ARG CONFIG_PATH

RUN pip install git+https://github.com/bogdandm/telegram-logging-bot.git --upgrade # v0.01
ADD $CONFIG_PATH /tmp/config.json
ENV CONFIG_PATH=/tmp/config.json
