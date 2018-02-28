# Telegram Logging Bot
Allows to get debug information from service throw redis pubsub protocol

## Installing
### Pip
_Package will publish after first stable release_

`pip install git+https://github.com/bogdandm/telegram-logging-bot.git`

```
# Set up env variables
...
pyton -m telegram_logging.bot
```

### Docker
Pull `bogdandm/telegramloggingbot:latest` (`:dev`, `:release`)

or manually build

```bash
git clone https://github.com/bogdandm/telegram-logging-bot.git
cd telegram-logging-bot
docker build . --build-arg CONFIG_BUILD_PATH=<your_config_json_path>
```

### docker-compose
See `docker-compose.yml`

## Settings
- _(env)_ `DEBUG` - 0 or 1 - Set logger level to WARNING or DEBUG
- _(env)_ `TELEGRAM_TOKEN` - telegram bot token. Could be read from filesystem if value is a absolute filesystem path.
- _(env)_ `TELEGRAM_ACCESS_PASSWORD` - password for user auth. 
Could be read from filesystem if value is a absolute filesystem path.
- _(env)_ `CONFIG_PATH` - path to JSON config
    - `REDIS` - arguments for redis connection (see [StrictRedis](http://redis-py.readthedocs.io/en/latest/#redis.StrictRedis))
    - `AUTOSAVE` \[seconds\] - data autosave interval.    
     _Note:_ Chat and user data will be saved automatically on normal shutdown.
    - `REDIS_CHANNEL` redis pubsub channel for listening
    - `BACKUP_PATH` - path to save data. In Docker container point to a volume/mounted directory.
    
## Usage
1. `/start` - Entry point
2. Entry access password
3. `/listen` - Subscribe for error notifications
4. `/unlisten` - Unsubscribe 

## Built With
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [redis-py](https://github.com/andymccurdy/redis-py)

## License
This project is licensed under the MIT License - see the LICENSE.md file for details

## States workflow:
```
START -> WAIT_PASSWORD <-> AUTHORIZED <-> LISTENING
                 ^                            |
                 |                            |
                 ------------------------------
```