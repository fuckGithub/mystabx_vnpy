版本号：v6.7.13_MacOS_20260529 15:38:00
1. 说明

本次更新内容:

测评版与生产版合并，通过交易API通过函数CreateFtdcTraderApi，行情API通过函数 CreateFtdcMdApi的参数设置版本。

macOS版本函数ReqUserLogin参数修改，通过内嵌采集代码，已经无需嵌入采集模块单独采集信息。

交易API新增接口如下：
新增接口：
	投资者申报费阶梯收取记录查询，ReqQryInvestorInfoCommRec
	组合腿信息查询，ReqQryCombLeg
	对冲设置请求， ReqOffsetSetting
	对冲设置撤销请求， ReqCancelOffsetSetting
	投资者对冲设置查询， ReqQryOffsetSetting
	申请短信验证码请求， ReqGenSMSCode
	套利确认请求， ReqSpdApply
	套利确认撤销请求， ReqSpdApplyAction
	套利确认查询请求， ReqQrySpdApply
	套保确认请求，  ReqHedgeCfm
	套保确认撤销请求， ReqHedgeCfmAction
	套保确认查询请求， ReqQryHedgeCfm

2. 开发环境要求

开发者需要配置Xcode开发环境，否则采集模块可能无法正常使用。

3. 操作系统要求

要求操作系统为MacOS 10.15以上版本。

4. 应用权限配置

信息采集模块采集信息时，需要应用具备某些权限。若应用不具备某些权限，
可能会导致获取到对应的采集项为空。因此在使用信息采集模块前， 请使用者申请权限。
包括允许应用访问网络权限。


5. 支持架构

SDK支持x86_64和arm64。

6. 如何使用API和采集模块

将交易api和行情api以及信息采集模块导入项目中。


7. 替换动态库可能出现的问题

 7.1. 头文件找不到
修改引入头文件如下：
#import "thosttraderapi_se/ThostFtdcTraderApi.h"

 7.2. 程序运行失败
选择 TARGETAS > General > Frameworks,Libraries,and Embedded Content
设置 SDK Embed 为 Embed & Sign。





