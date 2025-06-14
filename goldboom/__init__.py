import json
import asyncio
from aiocqhttp.message import MessageSegment
from hoshino.service import Service
from hoshino.typing import HoshinoBot, CQEvent as Event
from hoshino.util import silence
from random import randint, shuffle
from itertools import cycle
from hoshino import R
from ..utils import chain_reply, saveData, loadData
from .._R import get, userPath
import sys
import os
from .. import money, config
from hoshino.config import SUPERUSERS
import time

sv = Service('���ը��', visible=True, enable_on_default=True)
no = get('emotion/no.png').cqcode
ok = get('emotion/ok.png').cqcode
# ��Ϸ�Ự����
game_sessions = {}  # {group_id: {session_id: ���ը��session}}
session_id_counter = 0 # ��������Ψһ�ĻỰID
MAX_POT_LIMIT = 1000 #��󽱳�
PENALTY = 1000 #ʧ�ܳͷ�
TIMEOUT = 300 # ��ʱʱ��

# ���ը���Ự��
class GoldBombSession:
    def __init__(self, group_id, starter_id, bot):
        global session_id_counter
        session_id_counter += 1
        self.session_id = session_id_counter #����Ψһ�ĻỰID
        self.group_id = group_id
        self.starter_id = starter_id
        self.bot = bot  # HoshinoBot ʵ��
        self.players = {}  # {user_id: pot_amount}  ÿ����ҵĽ�ҽ���
        self.player_order = [] # ���˳���б�
        self.is_running = False # ��Ϸ�Ƿ���������
        self.prepared = {}  # {user_id: True/False}  ����Ƿ�׼��
        self.failed = {} # {user_id: True/False} ����Ƿ�ʧ��
        self.all_stopped = False # ����Ƿ�ֹͣ��ע
        self.turn = None  # ��ǰ�غ����
        self.task = None  # ��ʱ����
        self.start_time = None # ��¼��Ϸ��ʼ��ʱ��

    async def start(self):
        self.is_running = True # �����Ϸ��ʼ
        self.start_time = time.time()  # ��¼��Ϸ��ʼ��ʱ��
        self.player_order = list(self.players.keys())
        shuffle(self.player_order)  # �������˳��
        self.turn = cycle(self.player_order) # ������ע�����
        await self.next_turn()  # ��ʼ��һ�غ�
        self.set_timer() # ������ʱ����

    async def next_turn(self):
        # �ҵ���һ��û��ʧ�ܵ����
        while True:
            # ����Ƿ�������Ҷ�ʧ��
            if all(self.failed.get(user_id, False) for user_id in self.players):
                await self.end_game()
                break

            # �����жϣ����ֻʣһ������Ҹ������ʧ�ܣ��������Ϸ
            if len(self.player_order) == 0:
                 await self.end_game()
                 break
            try:

                next_player = next(self.turn)
                if not self.failed.get(next_player, False): # ȷ�����û��ʧ��
                    self.current_player = next_player
                    await self.bot.send_group_msg(group_id=self.group_id, message=f'�ֵ� {MessageSegment.at(self.current_player)} ��ע (��ע/ֹͣ��ע)��')
                    break # �ҵ���һ����ң�����ѭ��
            except StopIteration:  # ������Ҷ�ֹͣ��ע��ʧ��
                await self.end_game()
                break # ����ѭ��
            except Exception as e:
                print(f"next_turn error: {e}")
                await self.end_game()
                break

    async def bet(self, user_id):
        if user_id != self.current_player:
            await self.bot.send_group_msg(group_id=self.group_id, message=f'��û�ֵ�����ע��');
            return

        amount = randint(100, 500)
        current_pot = self.players[user_id]
        new_pot = current_pot + amount

        if new_pot > MAX_POT_LIMIT:
            self.failed[user_id] = True # ������ʧ��
            self.players[user_id] = MAX_POT_LIMIT # ���ع̶�Ϊ����
            await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} ��ע {amount} ��ң��������ޣ��ж�ʧ�ܣ��Ѵﵽ{MAX_POT_LIMIT}��ң���ֹ������ע��')

            #�����˳�����Ƴ�����ֹ����ѭ��
            if user_id in self.player_order:
                self.player_order.remove(user_id)

            await self.next_turn() # �ֵ���һλ���

        else:
            self.players[user_id] = new_pot
            await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} ��ע {amount} ��ң�Ŀǰ���� {new_pot}��')
            await self.next_turn()

    async def stop_bet(self, user_id):
        if user_id not in self.players:
            return

        self.player_order.remove(user_id) # �����˳�����Ƴ�
        if not self.player_order: # ���������Ҷ�ֹͣ��ע
            await self.end_game()
            return

        # �����ֻ���
        self.turn = cycle(self.player_order)
        await self.next_turn()

    async def end_game(self):
        if not self.is_running:
            return

        self.is_running = False
        await self.bot.send_group_msg(group_id=self.group_id, message='���������ֹͣ��ע��ʧ�ܣ����ڽ���...')

        winner = None
        min_diff = float('inf')
        all_failed = True  # Ĭ�������˶�ʧ��

        # Ѱ����������������
        for user_id, pot in self.players.items():
            if not self.failed.get(user_id, False):  # �ų�ʧ�ܵ����
                all_failed = False  # ������һ����ûʧ��
                diff = MAX_POT_LIMIT - pot
                if diff < min_diff:
                    min_diff = diff
                    winner = user_id

        # �ж�ʤ��
        if all_failed:
            message = '������Ҷ�ʧ���ˣ���Ϸ���֣�ÿ�˿۳�1000��ҡ�\n'
            for user_id in self.players:
                money.reduce_user_money(user_id, 'gold', PENALTY)
                message += f'{MessageSegment.at(user_id)} �۳� {PENALTY} ��ҡ�\n'
            await self.bot.send_group_msg(group_id=self.group_id, message=message)

        else:
            message = f'��ϲ {MessageSegment.at(winner)} ��ʤ����ý����е����н�ң�\n'
            wining_money = self.players[winner]
            money.increase_user_money(winner, 'gold', wining_money)
            message += f'��� {wining_money} ��ҡ�\n'
            for user_id in self.players:
                if user_id != winner:
                     money.reduce_user_money(user_id, 'gold', PENALTY)
                     message += f'{MessageSegment.at(user_id)} �۳� {PENALTY} ��ҡ�\n'
            await self.bot.send_group_msg(group_id=self.group_id, message=message)

        # ����Ự
        self.cancel_timer()
        del game_sessions[self.group_id][self.session_id]
        if not game_sessions[self.group_id]:
            del game_sessions[self.group_id]

    async def close(self):
        if not self.is_running:
            return

        self.is_running = False
        await self.bot.send_group_msg(group_id=self.group_id, message='��Ϸ�ѹرա�')

        self.cancel_timer() #ȡ����ʱ����
        del game_sessions[self.group_id][self.session_id]
        if not game_sessions[self.group_id]:
            del game_sessions[self.group_id]

    # ��ʱ����
    async def auto_close(self):
        if self.is_running:  # ֻ�е���Ϸ��������ʱ��ִ��
            if time.time() - self.start_time >= TIMEOUT: # ����Ƿ�ʱ
                await self.bot.send_group_msg(group_id=self.group_id, message='��Ϸ�Ự��ʱ���Զ��رա�')
                await self.close()

    def set_timer(self):
        self.task = asyncio.ensure_future(self.auto_close_loop())
        self.task.set_name(f"���ը��-{self.group_id}-{self.session_id}") #������������

    async def auto_close_loop(self):
        while self.is_running:
            await asyncio.sleep(60)  # ÿ��60����һ���Ƿ�ʱ
            await self.auto_close()

    def cancel_timer(self):
        if self.task:
            self.task.cancel()

    async def player_ready(self, user_id):
        if user_id not in self.players:
            await self.bot.send_group_msg(group_id=self.group_id, message='�㻹û�м�����Ϸ��')
            return

        self.prepared[user_id] = True # ��������׼��
        await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} ��׼����')

        if len(self.players) >= 2 and all(self.prepared.values()): # ����Ƿ�������Ҷ���׼��
            await self.bot.send_group_msg(group_id=self.group_id, message='���������׼������Ϸ������ʼ...')
            await self.start()

    async def player_quit(self, user_id):
        if user_id not in self.players:
            await self.bot.send_group_msg(group_id=self.group_id, message='�㻹û�м�����Ϸ��')
            return

        if self.is_running: # ��Ϸ�Ѿ���ʼ
            await self.bot.send_group_msg(group_id=self.group_id, message='��Ϸ�Ѿ���ʼ���޷��˳���')
            return

        del self.players[user_id] # �Ƴ����
        if user_id in self.prepared:
            del self.prepared[user_id]

        await self.bot.send_group_msg(group_id=self.group_id, message=f'{MessageSegment.at(user_id)} �˳�����Ϸ��')

        if not self.players: # û�������
            await self.close()

# ָ���
@sv.on_fullmatch('���ը��')
async def start_game(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id in game_sessions and game_sessions[group_id]:
        await bot.send(ev, '��ǰȺ���н����еĽ��ը����Ϸ��')
        return

    # �����µ���Ϸ�Ự
    session = GoldBombSession(group_id, user_id, bot)

    # ��ʼ���Ự
    if group_id not in game_sessions:
        game_sessions[group_id] = {}
    game_sessions[group_id][session.session_id] = session

    await bot.send(ev, f'���ը����Ϸ�ѷ��𣬵ȴ���Ҽ��룬���͡�������Ϸ��������Ϸ��')

@sv.on_fullmatch('������Ϸ')
async def join_game(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id
    user_gold = money.get_user_money(user_id, 'gold')
    if user_gold<1000:
        await bot.send(ev, '��û���㹻�Ķ����...' + no)
        return
    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ�����͡����ը����������Ϸ��')
        return

    # ��ȡ��ǰ�Ự
    session = list(game_sessions[group_id].values())[0] #ֻȡ��һ��

    if user_id in session.players:
        await bot.send(ev, '���Ѿ���������Ϸ��')
        return

    if len(session.players) >= 3:
        await bot.send(ev, '��Ϸ����������')
        return

    # �������
    session.players[user_id] = 0  # ��ʼ��ҽ���Ϊ0
    session.prepared[user_id] = False  # ��ʼΪδ׼��
    session.failed[user_id] = False # ��ʼΪδʧ��

    await bot.send(ev, f'{MessageSegment.at(user_id)} ������Ϸ����ǰ���� {len(session.players)}/3���뷢��"׼��"��ʼ��Ϸ')

@sv.on_fullmatch('׼��')
async def player_ready(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ��')
        return

    session = list(game_sessions[group_id].values())[0]
    if session.is_running:
        await bot.send(ev, '��Ϸ�Ѿ���ʼ�ˡ�')
        return

    await session.player_ready(user_id)

@sv.on_fullmatch('�˳���Ϸ')
async def player_quit(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ��')
        return

    session = list(game_sessions[group_id].values())[0]
    await session.player_quit(user_id)

@sv.on_fullmatch('��ע')
async def bet(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ��')
        return

    session = list(game_sessions[group_id].values())[0]
    if not session.is_running:
        await bot.send(ev, '��Ϸ��δ��ʼ����ȴ��������׼����')
        return

    await session.bet(user_id)

@sv.on_fullmatch('ֹͣ��ע')
async def stop_bet(bot: HoshinoBot, ev: Event):
    group_id = ev.group_id
    user_id = ev.user_id

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ��')
        return

    session = list(game_sessions[group_id].values())[0]
    if not session.is_running:
         await bot.send(ev, '��Ϸ��δ��ʼ����ȴ��������׼����')
         return
    await bot.send(ev, f'{MessageSegment.at(user_id)} ֹͣ��ע��')
    await session.stop_bet(user_id)
    
    
@sv.on_prefix('�ر���Ϸ')
async def close_game_by_admin(bot: HoshinoBot, ev: Event):
    """
    ����Աֱ�ӹرյ�ǰȺ���еĽ��ը���Ự��
    """
    group_id = ev.group_id
    user_id = ev.user_id

    if user_id not in SUPERUSERS:
        await bot.send(ev, "ֻ�й���Ա����ʹ�ô�ָ�", at_sender=True)
        return

    if group_id not in game_sessions or not game_sessions[group_id]:
        await bot.send(ev, '��ǰȺû�н����еĽ��ը����Ϸ��')
        return

    # �رյ�ǰȺ������н��ը���Ự
    sessions_to_close = list(game_sessions[group_id].items())  # ����һ�ݻỰ�б�����������޸��ֵ�
    for session_id, session in sessions_to_close:
        await session.close() #����ȷ�ر�session
        del game_sessions[group_id][session_id]  # ���ֵ���ɾ���Ự

    # ����Ƿ���Ҫɾ�� group_id ��Ӧ�ļ�
    if not game_sessions[group_id]:
        del game_sessions[group_id]

    await bot.send(ev, '����Ա�ѹرյ�ǰȺ�Ľ��ը����Ϸ��')
    
help_goldboom = '''
���ը����Ϸ������

����һ��������˲���Ľ�ҽ�����Ϸ��

**��Ϸ���̣�**
1.  ���͡����ը����������Ϸ��
2.  ��ҷ��͡�������Ϸ��������Ϸ��
3.  ������Ϸ����ҷ��͡�׼����ָ���������Ҷ�׼������Ϸ��ʼ��
4.  ����������͡���ע��ָ���������Լ����صĽ�ҡ�
5.  ÿ����ҵĽ�������Ϊ1000��ң����������������ж�ʧ�ܡ�
6.  ��ҿ��Է��͡�ֹͣ��ע��ָ����ǰ�����Լ�����ע��
7.  ��������Ҷ�ֹͣ��ע��ʧ�ܺ���Ϸ������δʧ�ܵ�����У����ؽ����ӽ����޵���һ�ʤ������Լ������е����н�ҡ�
8.  ʧ�ܵ���ҿ۳�1000��ҡ�
9.  ��Ϸ��ʼǰ����ҿ��Է��͡��˳���Ϸ��ָ���˳���Ϸ
10. �����Ϸ����3�������˲��������Զ��رջỰ��

**ָ���б�**
*   ���ը����������Ϸ
*   ������Ϸ��������Ϸ
*   ׼����׼����Ϸ
*   �˳���Ϸ���˳���Ϸ
*   ��ע�����ӽ��ؽ��
*   ֹͣ��ע��ֹͣ��ע
*   ���ը���������鿴��Ϸ����
'''
@sv.on_fullmatch('���ը������')
async def goldboom_help(bot, ev):
    """
        ��ȡ��Ϸ����
    """
    chain = []
    await chain_reply(bot, ev, chain, help_goldboom)
    await bot.send_group_forward_msg(group_id=ev.group_id, messages=chain)