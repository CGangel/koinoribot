from hoshino import Service
from hoshino.util import FreqLimiter
from .._interact import interact, ActSession
from .._R import get
from ..utilize import get_double_mean_money
from ..money import get_user_money, reduce_user_money, increase_user_money
from ..config import BLACKUSERS


sv = Service('�����-����')

no = get('emotion/no.png').cqcode

freq = FreqLimiter(10)

debug_mode = False  # ����ģʽ�������Ľ��

@sv.on_prefix('�����')
async def fa_hongbao(bot, ev):
    message = ev.message.extract_plain_text().strip()
    if not message:
        return
    if interact.find_session(ev, name='��Һ��'):
        session = interact.find_session(ev, name='��Һ��')
        if session.is_expire():

            # ʣ���Ǯ������������
            remain_money = sum(session.state['hb_list'])
            if not debug_mode:
                increase_user_money(session.state['owner'], 'gold', remain_money)
            session.close()
        else:
            await bot.send(ev, f'��ǰ����û����Ľ�Һ��~')
            return

    if ev.user_id in BLACKUSERS:
        await bot.send(ev, '\n����ʧ�ܣ��˻������ᣬ����ϵ����ԱѰ�������' +no, at_sender=True)
        return
    # �˴�Ϊ��ȴʱ���ж�
    if not freq.check(ev.user_id):
        await bot.send(ev, 'ʮ����֮��ֻ�ܷ�һ�����' + no)
        return

    money_and_mxuser = message.split()
    if len(money_and_mxuser) == 1:
        currency = message
        max_user = '5'
    else:
        currency = money_and_mxuser[0]
        max_user = money_and_mxuser[1]
    print(currency, max_user)

    if not str.isdigit(currency) or not str.isdigit(max_user):
        await bot.send(ev, 'Ҫ����������' + no)
        return

    currency = int(currency)
    max_user = int(max_user)

    group_info = await bot.get_group_info(group_id=ev.group_id, no_cache=True)

    if max_user <= 2 or max_user > group_info['member_count']:
        await bot.send(ev, '�����������' + no)
        return

    user_money = get_user_money(ev.user_id, 'gold')

    if currency <= max_user or currency > int(user_money):
        await bot.send(ev, '�����������' + no)
        return

    freq.start_cd(ev.user_id)

    if not debug_mode:
        reduce_user_money(ev.user_id, 'gold', currency)

    hongbao_list = get_double_mean_money(currency, max_user)
    session = ActSession.from_event('��Һ��', ev, usernum_limit = True, max_user = max_user, expire_time=600)
    interact.add_session(session)
    session.state['hb_list'] = hongbao_list
    session.state['owner'] = ev.user_id
    session.state['users'] = []

    user_info = await bot.get_group_member_info(group_id=ev.group_id, user_id=ev.user_id)
    nickname = user_info['nickname']

    await bot.send(ev, f'{nickname}����һ��{currency}ö��ҵĺ����һ����{max_user}��~\nʹ��"�����"����ȡ���')


@sv.on_prefix('�����')
async def qiang_hongbao(bot, ev):
    if not interact.find_session(ev, name='��Һ��'):
        return
    session = interact.find_session(ev, name='��Һ��')
    if session.is_expire():
        remain_money = sum(session.state['hb_list'])
        if not debug_mode:
            increase_user_money(session.state['owner'], 'gold', remain_money)
        await session.send(ev, f'������ڣ��ѷ���ʣ���{remain_money}ö���')
        session.close()
        return
    if ev.user_id in session.state['users']:
        await bot.send(ev, '���Ѿ���������ˣ�')
        return
    if session.state['hb_list']:
        user_gain = session.state['hb_list'].pop()
        session.state['users'].append(ev.user_id)
        if not debug_mode:
            increase_user_money(ev.user_id, 'gold', user_gain)
            await bot.send(ev, f'��������{user_gain}ö���~', at_sender=True)
    if not session.state['hb_list']:
        session.close()
        await bot.send(ev, '���������~')
        return







