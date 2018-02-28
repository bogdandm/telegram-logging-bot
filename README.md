# Telegram Logging Bot
Allows to get debug information from service throw redis pubsub protocol

## Installation
### Pip
_Package will publish after first stable release_

`pip install git+https://github.com/bogdandm/telegram-logging-bot.git` 

### Docker
`bogdandm/telegramloggingbot:latest`

**build argument** - `CONFIG_PATH` - path to `config.json` relative to `Dockerfile`

### docker-compose
See `docker-compose.yml`

## Settings
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
