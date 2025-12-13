import json
import sys
import asyncio
import aiohttp
import time
import random


class Player:
    def __init__(self):
        self.is_alive = True
        self.is_undercover = False
        self.word = None
        self.message = []
        pass


class GameManager:
    def __init__(self):
        self.llm_config = []
        self.player = 0
        self.undercover_player = 0
        self.player_info = []
        self.undercover_word = None
        self.normal_word = None
        self.now_speak_player = []
        self.devote_list = []
        pass

    def check_config(self):
        try:
            _exc = None
            config = self.read_config()
            self.llm_config = config["llm_config"]
        except json.JSONDecodeError as e:
            print("ERROR：文件不是合法json格式！")
            _exc = e
        except FileNotFoundError as e:
            print("ERROR：没有找到config.json文件！")
            _exc = e
        except KeyError as e:
            print("ERROR：json文件内容不正确！")
            _exc = e
        except TypeError as e:
            print("ERROR：json根类型必须是dict元素！")
            _exc = e
        except Exception as e:
            print(f"ERROR：未知问题:{e}")
            _exc = e
        finally:
            if _exc is not None:
                return False
        if not isinstance(config["llm_config"], list):
            return False
        for config in config["llm_config"]:
            if not isinstance(config, dict):
                return False
            if not ("url" in config and "model" in config and "key" in config):
                return False
            if not (
                isinstance(config["url"], str)
                and isinstance(config["model"], str)
                and isinstance(config["key"], str)
            ):
                return False

        self.player = len(self.llm_config)
        return True

    def read_config(self):
        with open("config.json", "r", encoding="utf-8") as f:
            dataset = json.load(f)
            return dataset

    def create_prompt(self, index):
        llm_prompt = [
            "**任务**：参与《谁是间谍》游戏。",
            "**身份**：你可能是**间谍**或**平民**，游戏开始时未知。",
            "**目标**：通过发言和投票淘汰敌对阵营成员，为本阵营争取胜利。",
            "**游戏流程**：",
            "1. 【发言阶段】：按编号发言，用一句话暗示你的词语，**不能直接说出词语**。",
            "2. 【投票阶段】：根据发言投票，得票最多者出局。平票则继续发言再投。",
            "**发言策略**：",
            "- **必须使用模糊、模棱两可的描述**，避免透露明确信息。",
            "- **鼓励猜测对方词语**，并在发言中故意误导他人。",
            "- **间谍应伪装成平民**，平民应隐藏真实词语，同时试探他人。",
            "- **发言应简短、具有误导性**，一句话即可，不要解释。",
            "**输入格式**：",
            "- 当输入以【发言阶段】开头时，你只需输出**一句话**（不含标点以外的内容）。",
            "- 当输入以【投票阶段】开头时，你只需输出**一个数字**（投票对象编号）。",
            "**注意事项**：",
            "- **欺骗、误导、模糊表达**是游戏的核心策略，不被视为违规。",
            "- 不要承认自己是间谍，也不要直接问他人身份。",
            "- 尽量从他人的发言中寻找矛盾点。",
            "**发言要求**：避免重复他人已用过的描述角度或表达方式。尽量从新颖的角度暗示你的词语。",
            f"**玩家配置**：共{self.player}人，{self.player - self.undercover_player}平民，{self.undercover_player}间谍。",
            "**胜利条件**：",
            "- 平民胜：所有间谍出局。",
            "- 间谍胜：存活平民 ≤ 存活间谍。",
            "请回复“确认”以开始游戏。",
            f"你的词语是：{self.player_info[index].word}，你的编号是：{index}",
        ]
        return "\n".join(llm_prompt)

    async def send_message(self, message, index):
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.llm_config[index]['key']}",
                "Content-Type": "application/json",
            }
            payload = {"messages": message, "model": self.llm_config[index]["model"]}
            retry = 0
            while retry < 3:
                try:
                    async with session.post(
                        url=self.llm_config[index]["url"], headers=headers, json=payload
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            raise Exception(f"HTTP error: {response.status}")
                except Exception as e:
                    print(f"ERROR:{e},retrying...")
                    retry += 1
        return None

    def create_undercover(self):
        for i in range(0, self.player):
            self.player_info.append(Player())
        undercovers = random.sample(range(0, self.player), self.undercover_player)
        print(f"undercover list:{undercovers}")
        for i, player in enumerate(self.player_info):
            if i in undercovers:
                player.is_undercover = True
                player.word = self.undercover_word
            else:
                player.word = self.normal_word
        return

    def create_speak_message(self, index, round):
        message_str = f"【发言阶段】\n现在是**第{round}轮**\n[本轮发言玩家有]\n"
        for i in self.now_speak_player:
            message_str += str(i)
            if i != self.now_speak_player[-1]:
                message_str += ","
        message_str += "\n[本轮已经发言的玩家有]\n"
        for i in range(0, index):
            if i not in self.now_speak_player:
                continue
            message_str += (
                f"玩家{i}:" + self.player_info[i].message[-1]["content"] + "\n"
            )
        message_str += "[现在轮到你发言]"
        return message_str

    async def speak_loop(self, round):
        for player in self.now_speak_player:
            play_str = self.create_speak_message(player, round)
            self.player_info[player].message.append(
                {"role": "user", "content": play_str}
            )
            result = await self.send_message(self.player_info[player].message, player)
            if result == None:
                sys.exit()
            print(
                f"player{player}描述词语：{result['choices'][0]['message']['content']}"
            )
            self.player_info[player].message.append(result["choices"][0]["message"])
        return

    def round_end(self):
        if self.devote_list == []:
            return None
        repeat_list = [0] * self.player
        for devoter in self.devote_list:
            repeat_list[devoter] += 1
        max_num = 0
        re_speak = []
        for i, devotee in enumerate(repeat_list):
            if devotee == max_num:
                re_speak.append(i)
            if devotee > max_num:
                max_num = devotee
                re_speak = [i]
        if len(re_speak) == 1:
            return re_speak[0]
        return re_speak

    def is_win(self):
        alive_undercover = 0
        alive_normal = 0
        for player in self.player_info:
            if player.is_alive:
                if player.is_undercover:
                    alive_undercover += 1
                else:
                    alive_normal += 1
        # 返回为1，平民胜利，2为间谍胜利，None为目前无胜利
        if alive_undercover == 0:
            return 1
        if alive_undercover >= alive_normal:
            return 2
        return None

    def devote_message(self):
        msg_str = "【投票阶段】\n本轮发言玩家有："
        for player in self.now_speak_player:
            msg_str += str(player)
            if player != self.now_speak_player[-1]:
                msg_str += ","
        msg_str += "\n这些玩家的发言如下：\n"
        for player in self.now_speak_player:
            msg_str += (
                f"编号{player}:{self.player_info[player].message[-1]['content']}\n"
            )
        msg_str += "请投票给一位玩家，**仅输出你选择的玩家编号**。"
        return msg_str

    def is_int(self, mystr):
        try:
            int(mystr)
        except ValueError:
            return False
        return True

    async def devote_stage(self):
        mssage = self.devote_message()
        for i, player in enumerate(self.player_info):
            if player.is_alive == False:
                continue
            player.message.append({"role": "user", "content": mssage})
            rusult = await self.send_message(player.message, i)
            if rusult == None:
                sys.exit()
            devote = rusult["choices"][0]["message"]["content"].strip()
            if self.is_int(devote) and int(devote) in self.now_speak_player:
                self.devote_list.append(int(devote))
            player.message.append(rusult["choices"][0]["message"])
        return

    async def main(self):
        random.seed(time.time())
        if not self.check_config():
            print("数据文件异常！程序退出")
            sys.exit()
        self.normal_word = input("平民词语：")
        self.undercover_word = input("间谍词语：")
        self.undercover_player = int(input("间谍数量："))
        self.create_undercover()
        for i, player in enumerate(self.player_info):
            player.message.append({"role": "system", "content": self.create_prompt(i)})
            result = await self.send_message(player.message, i)
            if result == None:
                sys.exit()
            if result["choices"][0]["message"]["content"] != "确认":
                sys.exit()
            player.message.append(result["choices"][0]["message"])
            print(f"player:{i} is ok!")
        # game started!
        round = 1
        while self.is_win() == None:
            print(f"---第{round}轮次开始---")
            out_player = 0
            self.devote_list = []
            while True:
                re_speak = self.round_end()
                if re_speak != None and isinstance(re_speak, int):
                    self.player_info[re_speak].is_alive = False
                    out_player = re_speak
                    break
                if re_speak == None:
                    re_speak = []
                    for i, player in enumerate(self.player_info):
                        if player.is_alive:
                            re_speak.append(i)
                re_speak.sort()
                self.now_speak_player = re_speak
                print(f"本轮发言人：{self.now_speak_player}")
                await self.speak_loop(round)
                self.devote_list = []
                await self.devote_stage()
            print(f"player{out_player}被淘汰！")
            round += 1
        if self.is_win() == 1:
            print("平民胜利！")
        else:
            print("间谍胜利！")
        sys.exit()


async def main():
    gamer = GameManager()
    await gamer.main()


if __name__ == "__main__":
    asyncio.run(main())
