#!/usr/bin/env python3
"""Build the original, scenario-based starter lexicon shipped with the skill."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from pathlib import Path


SCENARIOS = [
    ("social", "社交问候", "见面、寒暄、礼貌表达与澄清", """
hello|你好
hi|嗨；你好
good morning|早上好
good afternoon|下午好
good evening|晚上好
goodbye|再见
please|请
thank you|谢谢
you're welcome|不客气
excuse me|打扰一下；劳驾
sorry|对不起；抱歉
yes|是；好的
no|不；不是
maybe|也许
of course|当然
nice to meet you|很高兴认识你
how are you|你好吗
I'm fine|我很好
see you later|待会儿见；回头见
take care|保重；当心
introduce|介绍
invite|邀请
agree|同意
disagree|不同意
explain|解释
repeat|重复
speak slowly|说慢一点
I don't understand|我不明白
what do you mean|你是什么意思
that makes sense|这说得通
"""),
    ("family", "家庭与人际", "家人、朋友、关系与相处", """
family|家庭；家人
parent|父亲或母亲；家长
mother|母亲
father|父亲
child|孩子
son|儿子
daughter|女儿
brother|兄弟
sister|姐妹
husband|丈夫
wife|妻子
friend|朋友
neighbor|邻居
relative|亲戚
couple|夫妻；情侣
baby|婴儿
adult|成年人
married|已婚的
single|单身的
visit|拜访；看望
grow up|长大
get along|相处融洽
take care of|照顾
live together|住在一起
keep in touch|保持联系
trust|信任
support|支持
argue|争吵；争论
apologize|道歉
relationship|关系
"""),
    ("home", "居家日常", "房间、家务和日常起居", """
home|家
house|房子
room|房间
bedroom|卧室
bathroom|浴室；卫生间
kitchen|厨房
door|门
window|窗户
table|桌子
chair|椅子
bed|床
light|灯；光
key|钥匙
floor|地板；楼层
clean|打扫；干净的
wash|清洗
dry|使变干；干燥的
open|打开；开着的
close|关闭；靠近的
turn on|打开电器
turn off|关闭电器
wake up|醒来
get dressed|穿好衣服
make the bed|整理床铺
take a shower|洗淋浴
do the laundry|洗衣服
take out the trash|倒垃圾
tidy up|整理；收拾
run out of|用完；耗尽
feel at home|感觉自在
"""),
    ("food", "餐饮与厨房", "食物、点餐、烹饪和饮食需求", """
water|水
coffee|咖啡
tea|茶
milk|牛奶
bread|面包
rice|米饭；大米
fruit|水果
vegetable|蔬菜
meat|肉
chicken|鸡肉；鸡
fish|鱼；鱼肉
egg|鸡蛋
breakfast|早餐
lunch|午餐
dinner|晚餐
hungry|饿的
thirsty|渴的
delicious|美味的
menu|菜单
order|点餐；订单
cook|烹饪；厨师
cut|切
boil|煮沸；水煮
fry|煎；炸
bake|烘烤
taste|品尝；味道
ingredient|食材；原料
portion|一份；分量
takeout|外卖
dietary preferences|饮食偏好
"""),
    ("shopping", "购物与支付", "价格、尺码、付款、退换与客服", """
shop|商店；购物
price|价格
cash|现金
card|卡；银行卡
bag|袋子；包
size|尺码；大小
color|颜色
cheap|便宜的
expensive|昂贵的
buy|购买
sell|出售
pay|付款
cost|花费；成本
receipt|收据
change|零钱；找零
customer|顾客
discount|折扣
sale|促销；出售
try on|试穿
fit|合身；适合
return|退货；返回
exchange|换货；交换
in stock|有货
out of stock|缺货
compare prices|比较价格
pay by card|刷卡支付
keep the receipt|保留收据
a good deal|很划算的交易
refund|退款
checkout|结账处；结账
"""),
    ("time", "时间与日程", "日期、频率、约会与截止时间", """
today|今天
tomorrow|明天
yesterday|昨天
morning|早晨
afternoon|下午
evening|傍晚；晚上
night|夜晚
week|周
month|月
year|年
hour|小时
minute|分钟
early|早的；提前
late|迟的；晚的
now|现在
soon|很快
always|总是
usually|通常
sometimes|有时
never|从不
schedule|日程；安排
appointment|预约；约会
deadline|截止时间
on time|准时
be late for|迟到
once a week|每周一次
in advance|提前
free time|空闲时间
make time|腾出时间
put off|推迟
"""),
    ("transport", "交通与问路", "交通工具、方向、换乘和路况", """
car|汽车
bus|公共汽车
train|火车
subway|地铁
taxi|出租车
bicycle|自行车
station|车站
stop|站；停止
airport|机场
ticket|票
road|道路
street|街道
left|左边；向左
right|右边；向右
straight|直的；直走
near|近的；在附近
far|远的
drive|驾驶
ride|骑；乘坐
walk|步行
arrive|到达
leave|离开；出发
traffic|交通
platform|站台
get on|上车
get off|下车
transfer|换乘；转移
miss the bus|错过公交车
traffic jam|交通堵塞
how do I get to|我怎么去……
"""),
    ("travel", "旅行与住宿", "航班、酒店、行李和观光", """
trip|旅行
travel|旅行；出行
hotel|酒店
guest room|客房
passport|护照
luggage|行李
map|地图
flight|航班
beach|海滩
mountain|山
museum|博物馆
tourist|游客
reservation|预订
check in|办理入住；值机
check out|退房；结账离开
book a room|预订房间
pack|打包行李
unpack|打开行李
stay|停留；住宿
landmark|地标
sightseeing|观光
local|当地的；本地人
abroad|在国外
round trip|往返行程
one-way ticket|单程票
boarding pass|登机牌
carry-on luggage|随身行李
front desk|前台
fully booked|预订已满
recommend a place|推荐一个地方
"""),
    ("work", "工作与办公", "团队、任务、会议和项目推进", """
work|工作
job|工作；职位
office|办公室
company|公司
team|团队
boss|老板；上司
manager|经理
client|客户
colleague|同事
meeting|会议
email|电子邮件
task|任务
project|项目
report|报告
plan|计划
goal|目标
idea|想法
problem|问题
solution|解决方案
finish|完成
start|开始
send|发送
receive|收到
discuss|讨论
decide|决定
prioritize|确定优先顺序
follow up|跟进
work from home|居家办公
make progress|取得进展
be responsible for|负责……
"""),
    ("study", "学习与课堂", "读写、课堂、作业和学习策略", """
school|学校
class|课程；班级
teacher|老师
student|学生
book|书
notebook|笔记本
pen|笔
question|问题
answer|回答；答案
homework|家庭作业
test|测试；考试
lesson|课；课程内容
learn|学习；学会
study|学习；研究
read|阅读
write|写
listen|听
practice|练习
remember|记得
forget|忘记
example|例子
meaning|意思
pronounce|发音
take notes|记笔记
look up|查找
hand in|提交
figure out|弄明白
pay attention|注意
make a mistake|犯错
ask for help|寻求帮助
"""),
    ("health", "健康与就医", "身体、症状、看病和恢复", """
body|身体
head|头
face|脸
eye|眼睛
ear|耳朵
nose|鼻子
mouth|嘴
hand|手
foot|脚
back|背部
pain|疼痛
sick|生病的
healthy|健康的
doctor|医生
nurse|护士
medicine|药
hospital|医院
fever|发烧
cold|感冒
cough|咳嗽
hurt|疼；受伤
rest|休息
exercise|锻炼
feel better|感觉好些
have a headache|头疼
take medicine|服药
make an appointment|预约
allergy|过敏
side effect|副作用
recover|恢复；康复
"""),
    ("emotion", "情绪与性格", "感受、性格、压力与鼓励", """
happy|开心的
sad|难过的
angry|生气的
tired|疲倦的
afraid|害怕的
worried|担心的
excited|兴奋的
bored|无聊的
calm|冷静的
surprised|惊讶的
busy|忙的
relaxed|放松的
kind|友善的
funny|有趣的；好笑的
quiet|安静的
friendly|友好的
honest|诚实的
patient|有耐心的
confident|自信的
nervous|紧张的
proud|自豪的
disappointed|失望的
comfortable|舒服的；自在的
upset|难过的；心烦的
curious|好奇的
feel like|想要；感觉像
look forward to|期待
be interested in|对……感兴趣
deal with|处理；应对
cheer up|振作起来；使高兴
"""),
    ("digital", "手机与网络", "设备、账号、文件和联网操作", """
phone|手机；电话
computer|电脑
screen|屏幕
keyboard|键盘
mouse|鼠标
website|网站
app|应用程序
password|密码
message|消息
photo|照片
video|视频
file|文件
download|下载
upload|上传
click|点击
search|搜索
online|在线的
offline|离线的
link|链接
account|账号
log in|登录
log out|退出登录
sign up|注册
turn up the volume|调高音量
connect to Wi-Fi|连接无线网络
send a message|发送消息
save a file|保存文件
delete a file|删除文件
update the app|更新应用
run out of battery|没电了
"""),
    ("weather", "天气与自然", "季节、天气变化和户外环境", """
sun|太阳
rain|雨；下雨
snow|雪；下雪
wind|风
cloud|云
sky|天空
weather|天气
hot|热的
cold|冷的
warm|温暖的
cool|凉爽的
wet|湿的
dry|干燥的
season|季节
spring|春天
summer|夏天
autumn|秋天
winter|冬天
temperature|温度
forecast|天气预报；预测
sunny|晴朗的
rainy|下雨的
windy|有风的
cloudy|多云的
storm|暴风雨
heavy rain|大雨
clear up|转晴；清理
protect the environment|保护环境
outdoors|在户外
air quality|空气质量
"""),
    ("hobby", "兴趣与运动", "休闲、艺术、运动和周末活动", """
music|音乐
movie|电影
game|游戏
sport|运动
football|足球
basketball|篮球
swimming|游泳
running|跑步
walking|散步；步行
dance|跳舞
sing|唱歌
draw|画画
paint|绘画；涂色
photography|摄影
reading|阅读
cooking|烹饪
gardening|园艺
weekend|周末
hobby|爱好
fun|乐趣；有趣的
play|玩；演奏
watch|观看
listen to|听……
go for a walk|去散步
hang out|一起闲逛；聚会
spend time|花时间
join a club|加入社团
be good at|擅长
try something new|尝试新事物
take a break|休息一下
"""),
    ("clothing", "穿衣与洗护", "衣物、穿搭和随身物品", """
clothes|衣服
shirt|衬衫
T-shirt|T恤
pants|裤子
dress|连衣裙；穿衣
skirt|裙子
shoes|鞋
socks|袜子
coat|外套
hat|帽子
glasses|眼镜
wristwatch|手表
wear|穿；戴
put on|穿上；戴上
take off|脱下；取下
tight|紧的
loose|宽松的
dirty|脏的
match|搭配；匹配
style|风格
uniform|制服
umbrella|雨伞
wallet|钱包
backpack|双肩包
button|纽扣；按钮
zipper|拉链
get changed|换衣服
dress up|精心打扮
casual|休闲的
personal care|个人护理
"""),
    ("public", "公共服务与安全", "办事、求助、位置和紧急情况", """
police|警察
firefighter|消防员
bank|银行
post office|邮局
pharmacy|药店
library|图书馆
park|公园
toilet|洗手间
entrance|入口
exit|出口
help|帮助
danger|危险
safe|安全的
careful|小心的
lost|迷路的；丢失的
broken|坏了的
emergency|紧急情况
call the police|报警
call an ambulance|叫救护车
fire alarm|火警警报
first aid|急救
wait in line|排队等候
fill out a form|填写表格
show your ID|出示证件
opening hours|营业时间
customer service|客户服务
lost and found|失物招领处
across from|在……对面
between|在……之间
ask for directions|问路
"""),
    ("core", "核心动作与连接", "高频动词、逻辑连接和叙述顺序", """
do|做
make|制作；使得
get|得到；变得
give|给
take|拿；带走
bring|带来
keep|保持；保留
put|放置
use|使用
need|需要
want|想要
like|喜欢；像
know|知道；认识
think|思考；认为
feel|感觉
find|找到；发现
tell|告诉
ask|询问；请求
try|尝试
choose|选择
because|因为
but|但是
so|所以
if|如果
when|当……时；什么时候
before|在……之前
after|在……之后
first|首先；第一
then|然后
finally|最后
"""),
]


LEVEL_ORDER = {"A1": 0, "A2": 1, "B1": 2}


def entry_id(term: str, meaning: str) -> str:
    raw = "\0".join((unicodedata.normalize("NFKC", term).casefold().strip(), meaning.strip()))
    return "lex_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build() -> dict:
    scenario_rows = []
    entries: dict[tuple[str, str], dict] = {}
    for scenario_id, label, description, raw_rows in SCENARIOS:
        scenario_rows.append({"id": scenario_id, "label": label, "description": description})
        rows = [line.strip() for line in raw_rows.strip().splitlines() if line.strip()]
        if len(rows) != 30:
            raise ValueError(f"{scenario_id} must contain exactly 30 rows, found {len(rows)}")
        for index, row in enumerate(rows):
            term, meaning = (part.strip() for part in row.split("|", 1))
            level = "A1" if index < 12 else "A2" if index < 22 else "B1"
            key = (unicodedata.normalize("NFKC", term).casefold(), meaning)
            if key in entries:
                existing = entries[key]
                existing["scenario_ids"].append(scenario_id)
                if LEVEL_ORDER[level] < LEVEL_ORDER[existing["level"]]:
                    existing["level"] = level
                continue
            entries[key] = {
                "id": entry_id(term, meaning),
                "term": term,
                "meaning": meaning,
                "kind": "phrase" if " " in term else "word",
                "level": level,
                "scenario_ids": [scenario_id],
                "target_modes": ["recognition", "production"],
            }
    result = {
        "version": 1,
        "title": "生活英语起步词库",
        "description": "原创整理的基础词、短语和生活场景表达；难度为实用提示，不是官方考试评级。",
        "language_pair": "en-zh-CN",
        "scenarios": scenario_rows,
        "entries": list(entries.values()),
    }
    result["entry_count"] = len(result["entries"])
    return result


def main() -> int:
    output = Path(__file__).resolve().parents[1] / "data" / "starter-lexicon.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build()
    if payload["entry_count"] < 500:
        raise ValueError(f"starter lexicon unexpectedly small: {payload['entry_count']}")
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {payload['entry_count']} entries across {len(payload['scenarios'])} scenarios to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
