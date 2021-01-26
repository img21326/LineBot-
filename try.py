import configparser
config = configparser.ConfigParser()
config.read('config.ini')
hospitals = {}

for h in config['DEFAULT']['hospital'].split(','):
    channel_secret = config[h]['channel_secret']
    channel_access_token = config[h]['channel_access_token']
    redis_channel = config[h]['redis_channel']
    hospitals[h] = {
        'channel_secret': channel_secret,
        'channel_access_token': channel_access_token,
        'redis_channel': redis_channel,
    }

print(hospitals)