# FastapiAdmin v3.1.0 系统概述

FastapiAdmin 是一套全栈快速开发平台，包含 Web 管理后台、UniApp 小程序、Flutter 移动端。

## 技术栈

- 后端：FastAPI + SQLAlchemy 2.0 + MySQL/PostgreSQL
- 管理后台：Vue 3 + Element Plus + TypeScript
- 认证：JWT + OAuth2，SM2/SM3/SM4 国密加密
- 权限：RBAC 角色权限控制，支持数据权限隔离

## 核心功能模块

- 系统管理：用户、角色、菜单、部门、岗位、字典、参数、日志
- AI 管理：AI 供应商配置、AI 模型配置、智能对话
- 任务管理：定时任务、工作流编排
- 代码生成：根据数据库表结构生成前后端 CRUD 代码
- 应用门户：多应用管理入口

## 登录方式

- 用户名密码登录（SM2 加密传输，SM3 哈希存储）
- 手机号登录、扫码登录、OAuth 第三方登录

## API 规范

- 前缀：/api/v1
- 认证：Bearer Token（JWT）
- 限流：基于 Redis 的接口限流
