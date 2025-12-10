# 全自动AI养蛊姬

（不知道为什么叫这个名字）

总之，就是一个让AI自娱自乐玩谁是卧底的游戏

## 0.项目构建（从源码构建）

```bash
git clone https://github.com/Waterwzy/auto_undercover.git
cd auto_undercover
```

推荐python版本：

`3.12.10`

# 1.文件配置

文件 `config_example.json` 中提供了配置示例，具体来说：

- 你需要至少一个大语言模型的API服务

- 按照示例填写文件，具体来说：
  
  ```json
  {
      "llm_config": [
          {"model" : "第一个模型名称" , "url" : "对应的post请求的url" ,"key" : "对应的api-key"},
          {"model" : "第二个模型名称" , "url" : "对应的post请求的url" ,"key" : "对应的api-key"},
          ...
      ]
  }
  ```

- 你希望有多少玩家，就在这个列表中填入多少项，每项之间可以完全相同（使用同一个api服务）

> [!TIP]
> 
> 在代码中，实际读取的文件名为 `config.json` ，请注意更改文件名

## 2.开始游戏

```bash
python main.py
```

即可开始游戏。

在游戏开始前，你需要输入平民词汇，卧底词汇和卧底数量。

你可以查看卧底编号，并且实时查看玩家发言。

在达到胜利条件后，游戏自动退出

enjoy it :)
