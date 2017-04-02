import threading
import queue
import random

import itchat

# Start listening
itchat.auto_login()
threading.Thread(target = itchat.run).start()

username_to_user = {} # Map Wechat user name to WechatUser object

class WechatUser:
    def __init__(self, username):
        '''
        username: Wechat username
        '''
        self.msg_queue = queue.Queue() # Queue for messages
        self.username = username # Wechat username

        # Update the mapping
        username_to_user[username] = self

    def got_message(self, message):
        '''
        Called when new message is reveived.
        '''
        self.msg_queue.put(message)

    def send_message(self, message):
        '''
        Send message to user.
        '''
        if not message:
            message = '\n'*25 + '清屏'
            
        itchat.send(message, toUserName = self.username)

    def receive_message(self):
        '''
        Get message from user.
        '''
        return self.msg_queue.get() # Will block when there's no new message

    def get_input(self, message):
        '''
        Send message and get reply.
        '''
        if message:
            self.send_message(message)
        return self.receive_message()

    def get_int(self, message, min_value = -float('inf'), max_value = float('inf')):
        '''
        Get an intager in range(min_value, max_value)
        '''
        while True:
            try:
                result = int(self.get_input(message))
            except ValueError:
                self.send_message('这不是数字')
                continue
                
            if not(min_value <= result < max_value):
                self.send_message('超出范围')
                continue

            return result

    def decide(self, message = ''):
        '''
        Ask the player to select yes/no.
        '''
        if message:
            message += '(y/n)'

        answer = self.get_input(message)

        while True:
            if answer == 'Y' or answer == 'y':
                return True
            elif answer == 'N' or answer == 'n':
                return False
            else:
                self.message('请输入Y/y(yes)或者N/n(no)')


# Accept a new message from players
@itchat.msg_register(itchat.content.TEXT)
def listen_wechat_message(message):
    username = message['User']['UserName'] # User name of the Wechat user
    text = message['Text'] # Content of the message

    # Get remark name
    try:
        remarkname = message['User']['RemarkName']
    except KeyError:
        remarkname = None

    # If a user wants to enter the game
    if '进入游戏' in text:
        user = WechatUser(username)
        print('%s 作为 %s 进入了游戏' % (username, remarkname))

        threading.Thread(target = handle_request, args = (user,remarkname)).start()

    # If a user wants to edit configuration file
    else:
        try:
            user = username_to_user[username]
        except KeyError: # User didn't join the game
            print('无效的消息:%s %s\n%s' % (remarkname, username, text))
            return

        if '编辑配置' in text:
            print('%s 正在编辑配置' % remarkname)
            threading.Thread(target = edit_config, args = (user,)).start()

        elif '查看配置' in text:
            user.message(game_controller.str_identity_list())
    
        else:
            user.got_message(text)

def handle_request(user, remarkname):
    players = game_controller.players

    # Ask for remarkname if it's empty
    if not remarkname:
        remarkname = user.get_input('您没有备注名，请输入你的名字')
        print('%s 更名为 %s' % (user.username, remarkname))

    # Ask for the player's ID
    while True:
        player_id = user.get_int('请输入你的编号', 1, len(players))

        if players[player_id]:
            user.send_message('该编号已被占用')
            continue

        break
    
    # Assign an identity
    player = random.choice(game_controller.identity_pool)
    game_controller.identity_pool.remove(player)

    players[player_id] = player

    # Assign variables
    player.player_id = player_id
    player.user = user
    player.name = remarkname

    # Send message
    player.welcome()
    print('%s 已经上线' % player.desc())

def edit_config(user):
    if game_controller.game_started:
        user.send_message('游戏过程中不能编辑配置')
    else:
        game_controller.config.edit(user)

    print('配置编辑完成')
    game_controller.broadcast(game_controller.str_identity_list())
