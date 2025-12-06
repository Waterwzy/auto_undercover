import json
import sys
import asyncio
import aiohttp
import time
import random

class Player () :
    def __init__(self):
        self.is_alive = True
        self.is_undercover = False
        self.word = None
        self.message = []
        pass

class GameManager () :
    def __init__(self):
        self.llm_config = []
        self.player = 0
        self.undercover_player = 0
        self.player_info = []
        self.undercover_word = None
        self.normal_word = None
        pass

    def check_config(self) :
        try:
            _exc = None
            config = self.read_config()
            self.llm_config = config['llm_config']
        except json.JSONDecodeError as e :
            print("ERROR：文件不是合法json格式！")
            _exc = e
        except FileNotFoundError as e :
            print("ERROR：没有找到config.json文件！")
            _exc = e
        except KeyError as e :
            print("ERROR：json文件内容不正确！")
            _exc = e
        except TypeError as e :
            print("ERROR：json根类型必须是dict元素！")
            _exc = e
        except Exception as e :
            print(f"ERROR：未知问题:{e}")
            _exc = e
        finally :
            if _exc is not None :
                return False
        if not isinstance(config['llm_config'],list) :
            return False
        for config in config['llm_config'] :
            if not isinstance(config,dict) :
                return False
            if not ("url" in config and "model" in config and "key" in config) :
                return False
            if not (isinstance(config['url'],str) and isinstance(config['model'] , str) and isinstance(config['key'],str) ) :
                return False

        self.player = len(self.llm_config)
        return True

    def read_config(self) :
        with open("config.json","r",encoding='utf-8') as f:
            dataset = json . load(f)
            return dataset

    def create_prompt(self, index) :
            llm_prompt = [
                "**任务**：完成**谁是间谍**的游戏。",
                "**目标**：你是两个身份：**间谍**或者**平民**的其中一个，在游戏开始时，你并不知道自己的身份，你的目标是通过投票**淘汰与自己不同阵营的人**，取得胜利。",
                "**游戏过程**：在游戏开始，你会收到一个词语，**间谍与平民的不同之处在于收到的词语不同**，每轮游戏分为两个阶段：",
                "1. 阶段一**【发言阶段】**：在这个阶段，玩家将**按照编号依次发言，用一句与你收到的词语相关的话进行发言，但不能直接说出词语本身；并且通过其他玩家的发言找到与自己不同的玩家**",
                "2. 阶段二**【投票阶段】**：在这个阶段，玩家将**根据发言内容进行投票，每个玩家仅限投一票。得票最多的人出局**；当出现平票时，票数相同的玩家继续轮流发言并且投票，直到出局一人为止。",
                "**输入格式**：每次输入都会以【发言阶段】或者【投票阶段】开头，并详细阐述当前场上状况，其中：",
                "- 当输入为【发言阶段】时，你需要用**一句话描述你获得的词语**，并且直接输出，**不允许输出其他任何内容**",
                "- 当输入为【投票阶段】时，你需要**输出一个数字**，表明你要投票的玩家编号，**不允许输出包括其他文字或者标点符号在内的任何内容**",
                f"**玩家配置**：共计{self.player}名玩家，各自拥有从1-6的编号。其中{self.player - self.undercover_player}位平民，{self.undercover_player}位间谍",
                "**胜利条件**：当平民和间谍的任意一方达到胜利条件后，相关阵营胜利，游戏结束",
                "- 平民胜利条件：**所有**间谍出局",
                "- 间谍胜利条件：未出局的平民人数**小于或等于**未出局的间谍人数",
                "当你了解以上规则后，请输出“确认”，**不要输出其他字符**，以下是你的相关信息，游戏即将开始",
                f"你的词语是{self.player_info[index].word}，你的编号是{index}"
            ]
            return '\n'.join(llm_prompt)

    async def send_message(self , message , index ) :
        async with aiohttp.ClientSession() as session :
            headers = {
                "Authorization":f"Bearer {self.llm_config[index]['key']}",
                "Content-Type": "application/json"
            }
            payload = {
                "messages" : message,
                "model" : self.llm_config[index]['model']
            }
            retry = 0
            while retry < 3 :
                try:
                    async with session.post(
                        url=self.llm_config[index]['url'],
                        headers=headers,
                        json=payload
                    ) as response :
                        if response.status == 200 :
                            return await response.json()
                        else :
                            raise Exception(f"HTTP error: {response.status}")
                except Exception as e :
                    print(f"ERROR:{e},retrying...")
                    retry += 1
        return None

    def create_undercover(self) :
        for i in range (0 , self.player) :
            self.player_info.append(Player())
        undercovers = random.sample( range( 0 , self.player ) , self.undercover_player )
        for i,player in enumerate(self.player_info) :
            if i in undercovers :
                player.is_undercover = True
                player.word = self.undercover_word
            else :
                player.word = self.normal_word
        return

    async def main(self) :
        random.seed ( time.time( ) )
        if not self.check_config() :
            print("数据文件异常！程序退出")
            sys.exit()
        self.normal_word = input("平民词语：")
        self.unercover_word = input("间谍词语：")
        self.undercover_player = int ( input("间谍数量：" ) ) 
        self.create_undercover()
        for i,player in enumerate(self.player_info) :
            player.message.append({"role":"system" , "content" : self.create_prompt(i)})
            result = await self.send_message( player.message , i )
            if result == None :
                sys.exit()
            if result['choices'][0]['message']['content'] != "确认" :
                sys.exit()
            player.message.append(result['choices'][0]['message'])
            print(f"player:{i} is ok!")
        #game started!
        
        
async def main () :
    gamer = GameManager()
    await gamer.main()

if __name__ == "__main__" :
    asyncio.run(main())
