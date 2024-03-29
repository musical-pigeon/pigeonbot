# pyre-strict

# how to add: obtain a client ID (ask pigeon, or run the bot yourself), then visit:
# https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID_GOES_HERE&permissions=117760&scope=bot
# the permissions are: read messages/view channels, send msgs, embed links, attach files, read msg history
# channel history is so that it can check for imobot (we never ended up using this feature)

import json
import time
import os
import urllib

import discord
import toml

config = toml.load(open('cfg.toml'))
REQUIRED_CONFIG_KEYS=(
    'tag_file',
    'repost_file',
    'discord_token',

    'command_name__set',
    'command_name__get',
    'command_name__mike',

    'command_name__start',
    'start_response',
    'command_name__stop',
    'stop_response',

    'imobot_user_id',
    'wait_for_imobot',

    'repost_window',
)

# Encouraged, but not requred:
#    'danbooru_username',
#    'danbooru_api_key',
#    'gelbooru_user_id',
#    'gelbooru_api_key',

HEADERS={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'google.com',
}
MAX_NUM_ATTEMPTS=5

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

client = discord.Client(intents=intents)

def set_tag(user_id, tag):
    user_id = str(user_id)
    with open(config.get('tag_file'), 'r') as tag_file:
        lines = list(tag_file.read().splitlines())
    lines = [line for line in lines if not line.startswith(user_id)]
    lines.append(user_id + ' ' + tag)
    with open(config.get('tag_file'), 'w') as tag_file:
        tag_file.write('\n'.join(lines))

def get_tag(user_id):
    with open(config.get('tag_file'), 'r') as tag_file:
        for line in tag_file:
            if line.startswith(str(user_id)):
                return line.partition(' ')[2].strip()
    return None

async def is_imobot_active(message):
    if config.get('wait_for_imobot'):
        time.sleep(1)
        async for prev_message in message.channel.history(after=message):
            if prev_message.author.id == config.get('imobot_user_id'):
                return True
    return False

def try_danbooru(tag, rating_tag):
    try:
        url = 'https://danbooru.donmai.us/posts.json?page=1&limit=1&tags=order:random%20'
        url += tag + '%20' + rating_tag
        if 'danbooru_username' in config and 'danbooru_api_key' in config:
            url += '&login=' + urllib.parse.quote_plus(config.get('danbooru_username').encode()) +\
                    '&api_key=' + urllib.parse.quote_plus(config.get('danbooru_api_key').encode())
        req = urllib.request.Request(url)
        for k, v in HEADERS.items():
            req.add_header(k, v)
        res = urllib.request.urlopen(req)
        res_json = json.loads(res.read().decode('utf-8'))
        if len(res_json) > 0:
            post = res_json[0]
            post_url = 'https://danbooru.donmai.us/posts/' + str(post['id'])
            return (True, (post['file_url'], post_url, post['rating']))
        else:
            return (False, 'no images found')
    except BaseException as e:
        err = str(e)
        try:
            err_json = json.loads(e.read().decode('utf-8'))
            err += ' ' + err_json['message']
        except:
            pass
        return (False, err)

def try_gelbooru(tag, rating_tag):
    try:
        url = 'https://gelbooru.com/index.php?page=dapi&s=post&q=index&limit=1&pid=0&json=1&tags=sort:random%20'
        url += tag + '%20' + rating_tag
        if 'gelbooru_user_id' in config and 'gelbooru_api_key' in config:
            url += '&user_id=' + urllib.parse.quote_plus(config.get('gelbooru_user_id').encode()) +\
                    '&api_key=' + urllib.parse.quote_plus(config.get('gelbooru_api_key').encode())
        req = urllib.request.Request(url)
        for k, v in HEADERS.items():
            req.add_header(k, v)
        res = urllib.request.urlopen(req)
        res_json = json.loads(res.read().decode('utf-8'))
        if 'post' in res_json:
            post = res_json['post'][0]
            post_url = 'https://gelbooru.com/index.php?page=post&s=view&id=' + str(post['id'])
            return (True, (post['file_url'], post_url, post['rating']))
        else:
            return (False, 'no images found')
    except BaseException as e:
        err = str(e)
        try:
            err_json = json.loads(e.read().decode('utf-8'))
            err += ' ' + err_json['message']
        except:
            pass
        return (False, err)

recent_results = {}

def is_repost(user_id, image_url) -> bool:
    with open(config.get('repost_file'), 'r') as tag_file:
        contents = tag_file.read()
    result = image_url in contents.splitlines()
    if not result:
        contents += '\n' + image_url
    with open(config.get('repost_file'), 'w') as tag_file:
        tag_file.write(contents)

# awake, but at what cost
awake = True

@client.event
async def on_message(message):
    global awake

    if message.author == client.user:
        return

    if client.user in message.mentions and 'help' in message.content.lower():
        await message.channel.send('commands: ' + ', '.join([
            config.get('command_name__set'),
            config.get('command_name__get'),
            config.get('command_name__get') + 'x',
            config.get('command_name__get') + 'xxx', # :kongoulewd:
            config.get('command_name__mike'),
            config.get('command_name__mike') + 'x',
            config.get('command_name__mike') + 'xxx',
            config.get('command_name__start'),
            config.get('command_name__stop'),
        ]))

    if not awake:
        if client.user in message.mentions and config.get('command_name__start') in message.content:
            await message.channel.send(config.get('start_response'))
            awake = True
        else:
            return

    if client.user in message.mentions and config.get('command_name__stop') in message.content:
        awake = False
        await message.channel.send(config.get('stop_response'))
        return

    sanitized_msg = message.content.lower().strip()

    set_cmd_example = config.get('command_name__set') + ' danbooru_or_gelbooru_tag'
    if sanitized_msg.startswith(config.get('command_name__set')):
        response = ''
        words = message.content.split(' ')
        if len(words) < 2:
            response = 'use ' + set_cmd_example
        else:
            set_tag(message.author.id, urllib.parse.quote(message.content.partition(' ')[2]))
            response = 'tag set'
        if not await is_imobot_active(message):
            await message.channel.send(response)

    if sanitized_msg == config.get('command_name__get') or\
            sanitized_msg == config.get('command_name__get') + 'x' or\
            sanitized_msg == config.get('command_name__get') + 'xxx' or\
            sanitized_msg == config.get('command_name__mike') or\
            sanitized_msg == config.get('command_name__mike') + 'x' or\
            sanitized_msg == config.get('command_name__mike') + 'xxx':
        if sanitized_msg.startswith(config.get('command_name__get')):
            tag = get_tag(message.author.id)
            if tag is None:
                if not await is_imobot_active(message):
                    await message.channel.send('tag not set. use ' + set_cmd_example)
        else:
            assert sanitized_msg.startswith(config.get('command_name__mike'))
            tag = 'hatsune_miku'

        rating_tag = ''
        if sanitized_msg.endswith('xxx'):
            rating_tag = 'rating:explicit'
        elif sanitized_msg.endswith('x'):
            rating_tag = ''
        else:
            rating_tag = 'rating:general'

        counter = 0
        while True:
            (danbooru_worked, danbooru_img_or_err) = try_danbooru(tag, rating_tag)
            img = None
            if danbooru_worked:
                img = danbooru_img_or_err
            else:
                print('danbooru: ' + danbooru_img_or_err)
                (gelbooru_worked, gelbooru_img_or_err) = try_gelbooru(tag, rating_tag)
                if gelbooru_worked:
                    img = gelbooru_img_or_err
                else:
                    print('gelbooru: ' + gelbooru_img_or_err)
            if img is not None:
                if not await is_imobot_active(message):
                    if counter > MAX_NUM_ATTEMPTS or not is_repost(message.author.id, img[0]):
                        image_url = img[0]
                        post_url = img[1]

                        # danbooru's ratings are single-letter abbreviations ('explicit' -> 'e') of gelbooru's
                        is_explicit = img[2].startswith('e') or img[2].startswith('q')

                        if is_explicit and 'gelbooru' in image_url:
                            # gelbooru doesn't want us retrieving their images???
                            continue

                        if is_explicit:
                            # stupid discord API won't allow spoilers in embeds
                            # https://support.discord.com/hc/en-us/community/posts/360043419812-Ability-to-mark-as-spoiler-images-in-rich-embeds
                            local_image_path = image_url.rpartition('/')[2]
                            try:
                                urllib.request.urlretrieve(image_url, local_image_path)
                            except BaseException as e:
                                err = f'failed to retrieve image {image_url}: ' + str(e)
                                try:
                                    err += ' ' + e.read().decode('utf-8')
                                except:
                                    print('couldnt read it')
                                    pass
                                print(err)
                                await message.channel.send(err)
                                raise e
                            await message.channel.send(
                                content='<' + post_url + '>',
                                file=discord.File(local_image_path, spoiler=True)
                            )
                            os.remove(local_image_path)
                        else:
                            e = discord.Embed()
                            e.description = post_url
                            e.set_image(url=image_url)
                            await message.channel.send(embed=e)
                        break
            else:
                if not await is_imobot_active(message):
                    await message.channel.send('error. danbooru: ' + danbooru_img_or_err + ', gelbooru: ' + gelbooru_img_or_err)
                break
            counter += 1

client.run(config.get('discord_token'))
