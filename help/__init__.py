from hoshino import Service, priv
from hoshino.typing import CQEvent

sv = Service('_bqhelp_', manage_priv=priv.SUPERUSER, visible=False)
TOP_MANUAL = '''
= ����ʹ��˵�� =
�ɰ湦�ܣ�https://www.lanxy.ink/?p=476
\n���������뷢�ͣ�
\n�������\n���ɰ���\n�������\n���ը������
\n�������׬ȡ��ң��������Ծ����ִ̼��ġ�һ�����ġ��ɣ�
\n���˱һ�ȡ;�������㡢ǩ�������＼�ܡ�����Ť��
\n��ʯ��ȡ;������ʯ+���������＼��
\n���� �����Ʊ��� �����Լ���bot�����Ʊ���Ŀǰ��֧��yunzai��
'''.strip()
@sv.on_prefix('�������')
async def send_help(bot, ev: CQEvent):
    await bot.send(ev, TOP_MANUAL)
