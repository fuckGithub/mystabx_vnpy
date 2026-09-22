-- FastapiAdmin DDL — 2026-07-15
-- 使用方式: mysql -u root -p < fastapiadmin_ddl.sql

CREATE DATABASE IF NOT EXISTS `fastapiadmin` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `fastapiadmin`;

-- MySQL dump 10.13  Distrib 8.0.46, for macos26.4 (arm64)
--
-- Host: 127.0.0.1    Database: fastapiadmin
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `agno_runs`
--

DROP TABLE IF EXISTS `agno_runs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agno_runs` (
  `run_id` varchar(128) NOT NULL,
  `session_id` varchar(128) NOT NULL,
  `run_type` varchar(20) NOT NULL,
  `agent_id` varchar(128) DEFAULT NULL,
  `team_id` varchar(128) DEFAULT NULL,
  `workflow_id` varchar(128) DEFAULT NULL,
  `user_id` varchar(128) DEFAULT NULL,
  `parent_run_id` varchar(128) DEFAULT NULL,
  `status` varchar(50) DEFAULT NULL,
  `run_index` bigint DEFAULT NULL,
  `run_data` json NOT NULL,
  `created_at` bigint NOT NULL,
  `updated_at` bigint DEFAULT NULL,
  PRIMARY KEY (`run_id`),
  KEY `idx_agno_runs_created_at` (`created_at`),
  KEY `idx_agno_runs_agent_id` (`agent_id`),
  KEY `agno_runs_runs_session_id_run_index` (`session_id`,`run_index`),
  KEY `idx_agno_runs_team_id` (`team_id`),
  KEY `idx_agno_runs_workflow_id` (`workflow_id`),
  KEY `idx_agno_runs_user_id` (`user_id`),
  KEY `idx_agno_runs_status` (`status`),
  KEY `idx_agno_runs_session_id` (`session_id`),
  KEY `idx_agno_runs_run_type` (`run_type`),
  CONSTRAINT `agno_runs_ibfk_1` FOREIGN KEY (`session_id`) REFERENCES `agno_sessions` (`session_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `agno_schema_versions`
--

DROP TABLE IF EXISTS `agno_schema_versions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agno_schema_versions` (
  `table_name` varchar(128) NOT NULL,
  `version` varchar(10) NOT NULL,
  `created_at` varchar(128) NOT NULL,
  `updated_at` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`table_name`),
  KEY `idx_agno_schema_versions_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `agno_sessions`
--

DROP TABLE IF EXISTS `agno_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agno_sessions` (
  `session_id` varchar(128) NOT NULL,
  `session_type` varchar(20) NOT NULL,
  `agent_id` varchar(128) DEFAULT NULL,
  `team_id` varchar(128) DEFAULT NULL,
  `workflow_id` varchar(128) DEFAULT NULL,
  `user_id` varchar(128) DEFAULT NULL,
  `session_data` json DEFAULT NULL,
  `agent_data` json DEFAULT NULL,
  `team_data` json DEFAULT NULL,
  `workflow_data` json DEFAULT NULL,
  `metadata` json DEFAULT NULL,
  `runs` json DEFAULT NULL,
  `summary` json DEFAULT NULL,
  `created_at` bigint NOT NULL,
  `updated_at` bigint DEFAULT NULL,
  PRIMARY KEY (`session_id`),
  KEY `idx_agno_sessions_created_at` (`created_at`),
  KEY `idx_agno_sessions_session_type` (`session_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ai_model`
--

DROP TABLE IF EXISTS `ai_model`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_model` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `provider_id` int NOT NULL COMMENT '所属供应商ID',
  `model_key` varchar(128) NOT NULL COMMENT '模型id（如 mimo-v2.5）',
  `name` varchar(128) NOT NULL COMMENT '模型显示名（如 mimo-v2.5-tp）',
  `url` varchar(255) DEFAULT NULL COMMENT '模型端点地址（可覆盖供应商默认）',
  `tool_calling` tinyint(1) DEFAULT NULL COMMENT '是否支持工具调用',
  `vision` tinyint(1) DEFAULT NULL COMMENT '是否支持视觉/图片输入',
  `max_input_tokens` int DEFAULT NULL COMMENT '最大输入token数',
  `max_output_tokens` int DEFAULT NULL COMMENT '最大输出token数',
  `thinking` tinyint(1) DEFAULT NULL COMMENT '是否启用思考模式（推理模型）',
  `temperature` float DEFAULT NULL COMMENT '温度（默认0.7）',
  `is_default` tinyint(1) DEFAULT NULL COMMENT '是否为默认模型',
  `sort_order` int DEFAULT NULL COMMENT '排序号（越大越靠前）',
  `status` varchar(10) NOT NULL DEFAULT '0' COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已删除',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`),
  KEY `provider_id` (`provider_id`),
  CONSTRAINT `ai_model_ibfk_1` FOREIGN KEY (`provider_id`) REFERENCES `ai_provider` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI模型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ai_provider`
--

DROP TABLE IF EXISTS `ai_provider`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ai_provider` (
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `name` varchar(64) NOT NULL COMMENT '供应商名称（如 mimo-tp / DeepSeek）',
  `vendor` varchar(32) NOT NULL COMMENT '厂商类型(openai/anthropic/google/ollama/deepseek/customendpoint等)',
  `api_type` varchar(32) NOT NULL DEFAULT 'chat-completions' COMMENT 'API协议类型(chat-completions/messages/gemini/ollama/azure等)',
  `api_key` varchar(255) DEFAULT NULL COMMENT '供应商API密钥（模型级可覆盖）',
  `base_url` varchar(255) DEFAULT NULL COMMENT '供应商默认API地址（模型可覆盖）',
  `is_default` tinyint(1) DEFAULT NULL COMMENT '是否为默认供应商',
  `sort_order` int DEFAULT NULL COMMENT '排序号（越大越靠前）',
  `status` varchar(10) NOT NULL DEFAULT '0' COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否已删除',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='AI供应商表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `app_portal`
--

DROP TABLE IF EXISTS `app_portal`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `app_portal` (
  `name` varchar(64) NOT NULL COMMENT '应用名称',
  `access_url` varchar(500) NOT NULL COMMENT '访问地址',
  `icon_url` varchar(300) DEFAULT NULL COMMENT '应用图标URL',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `tenant_id` int NOT NULL COMMENT '租户ID',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_app_portal_uuid` (`uuid`),
  KEY `ix_app_portal_tenant_id` (`tenant_id`),
  KEY `ix_app_portal_deleted_id` (`deleted_id`),
  KEY `ix_app_portal_created_id` (`created_id`),
  KEY `ix_app_portal_updated_time` (`updated_time`),
  KEY `ix_app_portal_is_deleted` (`is_deleted`),
  KEY `ix_app_portal_id` (`id`),
  KEY `ix_app_portal_status` (`status`),
  KEY `ix_app_portal_updated_id` (`updated_id`),
  KEY `ix_app_portal_created_time` (`created_time`),
  KEY `ix_app_portal_deleted_time` (`deleted_time`),
  CONSTRAINT `app_portal_ibfk_1` FOREIGN KEY (`tenant_id`) REFERENCES `sys_tenant` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `app_portal_ibfk_2` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `app_portal_ibfk_3` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `app_portal_ibfk_4` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='门户应用';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `apscheduler_jobs`
--

DROP TABLE IF EXISTS `apscheduler_jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `apscheduler_jobs` (
  `id` varchar(191) NOT NULL,
  `next_run_time` double DEFAULT NULL,
  `job_state` blob NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_apscheduler_jobs_next_run_time` (`next_run_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_demo`
--

DROP TABLE IF EXISTS `gen_demo`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_demo` (
  `name` varchar(64) NOT NULL COMMENT '名称',
  `a` int DEFAULT NULL COMMENT '整数',
  `b` bigint DEFAULT NULL COMMENT '大整数',
  `c` float DEFAULT NULL COMMENT '浮点数',
  `d` tinyint(1) NOT NULL COMMENT '布尔型',
  `e` date DEFAULT NULL COMMENT '日期',
  `f` time DEFAULT NULL COMMENT '时间',
  `g` datetime DEFAULT NULL COMMENT '日期时间',
  `h` text COMMENT '长文本',
  `i` json DEFAULT NULL COMMENT '元数据(JSON格式)',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_gen_demo_uuid` (`uuid`),
  KEY `ix_gen_demo_updated_id` (`updated_id`),
  KEY `ix_gen_demo_updated_time` (`updated_time`),
  KEY `ix_gen_demo_is_deleted` (`is_deleted`),
  KEY `ix_gen_demo_id` (`id`),
  KEY `ix_gen_demo_status` (`status`),
  KEY `ix_gen_demo_deleted_id` (`deleted_id`),
  KEY `ix_gen_demo_created_time` (`created_time`),
  KEY `ix_gen_demo_deleted_time` (`deleted_time`),
  KEY `ix_gen_demo_created_id` (`created_id`),
  CONSTRAINT `gen_demo_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_demo_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_demo_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='示例表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_demo01`
--

DROP TABLE IF EXISTS `gen_demo01`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_demo01` (
  `name` varchar(64) NOT NULL COMMENT '名称',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_gen_demo01_uuid` (`uuid`),
  KEY `ix_gen_demo01_deleted_time` (`deleted_time`),
  KEY `ix_gen_demo01_updated_time` (`updated_time`),
  KEY `ix_gen_demo01_deleted_id` (`deleted_id`),
  KEY `ix_gen_demo01_id` (`id`),
  KEY `ix_gen_demo01_is_deleted` (`is_deleted`),
  KEY `ix_gen_demo01_created_time` (`created_time`),
  KEY `ix_gen_demo01_updated_id` (`updated_id`),
  KEY `ix_gen_demo01_created_id` (`created_id`),
  KEY `ix_gen_demo01_status` (`status`),
  CONSTRAINT `gen_demo01_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_demo01_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_demo01_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='示例1表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_table`
--

DROP TABLE IF EXISTS `gen_table`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_table` (
  `table_name` varchar(200) NOT NULL COMMENT '表名称',
  `table_comment` varchar(500) DEFAULT NULL COMMENT '表描述',
  `class_name` varchar(100) NOT NULL COMMENT '实体类名称',
  `package_name` varchar(100) DEFAULT NULL COMMENT '生成包路径',
  `module_name` varchar(30) DEFAULT NULL COMMENT '生成模块名',
  `business_name` varchar(30) DEFAULT NULL COMMENT '生成业务名',
  `function_name` varchar(100) DEFAULT NULL COMMENT '生成功能名',
  `sub_table_name` varchar(64) DEFAULT NULL COMMENT '关联子表的表名',
  `sub_table_fk_name` varchar(64) DEFAULT NULL COMMENT '子表关联的外键名',
  `parent_menu_id` int DEFAULT NULL COMMENT '父菜单ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_gen_table_uuid` (`uuid`),
  KEY `ix_gen_table_is_deleted` (`is_deleted`),
  KEY `ix_gen_table_status` (`status`),
  KEY `ix_gen_table_deleted_id` (`deleted_id`),
  KEY `ix_gen_table_created_time` (`created_time`),
  KEY `ix_gen_table_id` (`id`),
  KEY `ix_gen_table_deleted_time` (`deleted_time`),
  KEY `ix_gen_table_created_id` (`created_id`),
  KEY `ix_gen_table_updated_id` (`updated_id`),
  KEY `ix_gen_table_updated_time` (`updated_time`),
  CONSTRAINT `gen_table_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_table_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_table_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代码生成表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `gen_table_column`
--

DROP TABLE IF EXISTS `gen_table_column`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `gen_table_column` (
  `column_name` varchar(200) NOT NULL COMMENT '列名称',
  `column_comment` varchar(500) DEFAULT NULL COMMENT '列描述',
  `column_type` varchar(100) NOT NULL COMMENT '列类型',
  `column_length` varchar(50) DEFAULT NULL COMMENT '列长度',
  `column_default` varchar(200) DEFAULT NULL COMMENT '列默认值',
  `is_pk` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否主键',
  `is_increment` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否自增',
  `is_nullable` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否允许为空',
  `is_unique` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否唯一',
  `python_type` varchar(100) DEFAULT NULL COMMENT 'Python类型',
  `python_field` varchar(200) DEFAULT NULL COMMENT 'Python字段名',
  `is_insert` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否为新增字段',
  `is_edit` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否编辑字段',
  `is_list` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否列表字段',
  `is_query` tinyint(1) NOT NULL DEFAULT '0' COMMENT '是否查询字段',
  `query_type` varchar(50) DEFAULT NULL COMMENT '查询方式',
  `html_type` varchar(100) DEFAULT NULL COMMENT '显示类型',
  `dict_type` varchar(200) DEFAULT NULL COMMENT '字典类型',
  `sort` int NOT NULL COMMENT '排序',
  `table_id` int NOT NULL COMMENT '归属表编号',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_gen_table_column_uuid` (`uuid`),
  KEY `ix_gen_table_column_created_time` (`created_time`),
  KEY `ix_gen_table_column_status` (`status`),
  KEY `ix_gen_table_column_is_deleted` (`is_deleted`),
  KEY `ix_gen_table_column_updated_id` (`updated_id`),
  KEY `ix_gen_table_column_table_id` (`table_id`),
  KEY `ix_gen_table_column_id` (`id`),
  KEY `ix_gen_table_column_created_id` (`created_id`),
  KEY `ix_gen_table_column_updated_time` (`updated_time`),
  KEY `ix_gen_table_column_deleted_time` (`deleted_time`),
  KEY `ix_gen_table_column_deleted_id` (`deleted_id`),
  CONSTRAINT `gen_table_column_ibfk_1` FOREIGN KEY (`table_id`) REFERENCES `gen_table` (`id`) ON DELETE CASCADE,
  CONSTRAINT `gen_table_column_ibfk_2` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_table_column_ibfk_3` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `gen_table_column_ibfk_4` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代码生成表字段';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dept`
--

DROP TABLE IF EXISTS `sys_dept`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dept` (
  `name` varchar(64) NOT NULL COMMENT '部门名称',
  `order` int NOT NULL COMMENT '显示排序',
  `code` varchar(16) NOT NULL COMMENT '部门编码',
  `leader` varchar(32) DEFAULT NULL COMMENT '部门负责人',
  `phone` varchar(11) DEFAULT NULL COMMENT '手机',
  `email` varchar(64) DEFAULT NULL COMMENT '邮箱',
  `parent_id` int DEFAULT NULL COMMENT '父级部门ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  UNIQUE KEY `ix_sys_dept_uuid` (`uuid`),
  KEY `ix_sys_dept_updated_time` (`updated_time`),
  KEY `ix_sys_dept_parent_id` (`parent_id`),
  KEY `ix_sys_dept_is_deleted` (`is_deleted`),
  KEY `ix_sys_dept_status` (`status`),
  KEY `ix_sys_dept_created_time` (`created_time`),
  KEY `ix_sys_dept_deleted_time` (`deleted_time`),
  KEY `ix_sys_dept_id` (`id`),
  CONSTRAINT `sys_dept_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `sys_dept` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='部门表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dict_data`
--

DROP TABLE IF EXISTS `sys_dict_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dict_data` (
  `dict_sort` int NOT NULL COMMENT '字典排序',
  `dict_label` varchar(255) NOT NULL COMMENT '字典标签',
  `dict_value` varchar(255) NOT NULL COMMENT '字典键值',
  `css_class` varchar(255) DEFAULT NULL COMMENT '样式属性（其他样式扩展）',
  `list_class` varchar(255) DEFAULT NULL COMMENT '表格回显样式',
  `is_default` tinyint(1) NOT NULL COMMENT '是否默认（True是 False否）',
  `dict_type` varchar(255) NOT NULL COMMENT '字典类型',
  `dict_type_id` int NOT NULL COMMENT '字典类型ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_dict_data_uuid` (`uuid`),
  KEY `dict_type_id` (`dict_type_id`),
  KEY `ix_sys_dict_data_created_time` (`created_time`),
  KEY `ix_sys_dict_data_deleted_time` (`deleted_time`),
  KEY `ix_sys_dict_data_status` (`status`),
  KEY `ix_sys_dict_data_id` (`id`),
  KEY `ix_sys_dict_data_updated_time` (`updated_time`),
  KEY `ix_sys_dict_data_is_deleted` (`is_deleted`),
  CONSTRAINT `sys_dict_data_ibfk_1` FOREIGN KEY (`dict_type_id`) REFERENCES `sys_dict_type` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='字典数据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_dict_type`
--

DROP TABLE IF EXISTS `sys_dict_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_dict_type` (
  `dict_name` varchar(64) NOT NULL COMMENT '字典名称',
  `dict_type` varchar(255) NOT NULL COMMENT '字典类型',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `dict_type` (`dict_type`),
  UNIQUE KEY `ix_sys_dict_type_uuid` (`uuid`),
  KEY `ix_sys_dict_type_updated_time` (`updated_time`),
  KEY `ix_sys_dict_type_is_deleted` (`is_deleted`),
  KEY `ix_sys_dict_type_status` (`status`),
  KEY `ix_sys_dict_type_deleted_time` (`deleted_time`),
  KEY `ix_sys_dict_type_created_time` (`created_time`),
  KEY `ix_sys_dict_type_id` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='字典类型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_log`
--

DROP TABLE IF EXISTS `sys_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_log` (
  `type` int NOT NULL COMMENT '日志类型(1登录日志 2操作日志)',
  `request_path` varchar(255) NOT NULL COMMENT '请求路径',
  `request_method` varchar(10) NOT NULL COMMENT '请求方式',
  `request_payload` longtext COMMENT '请求体',
  `request_ip` varchar(50) DEFAULT NULL COMMENT '请求IP地址',
  `login_location` varchar(255) DEFAULT NULL COMMENT '登录位置',
  `request_os` varchar(64) DEFAULT NULL COMMENT '操作系统',
  `request_browser` varchar(64) DEFAULT NULL COMMENT '浏览器',
  `response_code` int NOT NULL COMMENT '响应状态码',
  `response_json` longtext COMMENT '响应体',
  `process_time` varchar(20) DEFAULT NULL COMMENT '处理时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  `signature` varchar(256) DEFAULT NULL COMMENT 'SM2签名值（国密完整性保护）',
  `signed_fields` varchar(512) DEFAULT NULL COMMENT '被签名字段标识（JSON格式）',
  `username` varchar(64) DEFAULT NULL COMMENT '操作人账号（冗余）',
  `mobile` varchar(11) DEFAULT NULL COMMENT '操作人手机号（冗余）',
  `login_platform` varchar(32) DEFAULT NULL COMMENT '登录平台(PC/FLUTTER/UNIAPP)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_log_uuid` (`uuid`),
  KEY `ix_sys_log_updated_time` (`updated_time`),
  KEY `ix_sys_log_updated_id` (`updated_id`),
  KEY `ix_sys_log_id` (`id`),
  KEY `ix_sys_log_deleted_id` (`deleted_id`),
  KEY `ix_sys_log_created_time` (`created_time`),
  KEY `ix_sys_log_deleted_time` (`deleted_time`),
  KEY `ix_sys_log_status` (`status`),
  KEY `ix_sys_log_is_deleted` (`is_deleted`),
  KEY `ix_sys_log_created_id` (`created_id`),
  CONSTRAINT `sys_log_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_log_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_log_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=115 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_menu`
--

DROP TABLE IF EXISTS `sys_menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_menu` (
  `name` varchar(50) NOT NULL COMMENT '菜单名称',
  `type` int NOT NULL COMMENT '菜单类型(1:目录 2:菜单 3:按钮/权限 4:链接)',
  `order` int NOT NULL COMMENT '显示排序',
  `permission` varchar(100) DEFAULT NULL COMMENT '权限标识(如:module_system:user:query)',
  `icon` varchar(50) DEFAULT NULL COMMENT '菜单图标',
  `route_name` varchar(100) DEFAULT NULL COMMENT '路由名称',
  `route_path` varchar(200) DEFAULT NULL COMMENT '路由路径',
  `component_path` varchar(200) DEFAULT NULL COMMENT '组件路径',
  `redirect` varchar(200) DEFAULT NULL COMMENT '重定向地址',
  `hidden` tinyint(1) NOT NULL COMMENT '是否隐藏(True:隐藏 False:显示)',
  `keep_alive` tinyint(1) NOT NULL COMMENT '是否缓存(True:是 False:否)',
  `always_show` tinyint(1) NOT NULL COMMENT '是否始终显示(True:是 False:否)',
  `title` varchar(50) DEFAULT NULL COMMENT '菜单标题',
  `params` json DEFAULT NULL COMMENT '路由参数(JSON对象)',
  `affix` tinyint(1) NOT NULL COMMENT '是否固定标签页(True:是 False:否)',
  `client` varchar(20) NOT NULL DEFAULT 'pc' COMMENT '终端(pc:管理端桌面 app:移动端)',
  `parent_id` int DEFAULT NULL COMMENT '父菜单ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_menu_uuid` (`uuid`),
  KEY `ix_sys_menu_deleted_time` (`deleted_time`),
  KEY `ix_sys_menu_id` (`id`),
  KEY `ix_sys_menu_parent_id` (`parent_id`),
  KEY `ix_sys_menu_updated_time` (`updated_time`),
  KEY `ix_sys_menu_is_deleted` (`is_deleted`),
  KEY `ix_sys_menu_status` (`status`),
  KEY `ix_sys_menu_created_time` (`created_time`),
  CONSTRAINT `sys_menu_ibfk_1` FOREIGN KEY (`parent_id`) REFERENCES `sys_menu` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=261 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='菜单表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_notice`
--

DROP TABLE IF EXISTS `sys_notice`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_notice` (
  `notice_title` varchar(64) NOT NULL COMMENT '公告标题',
  `notice_type` varchar(1) NOT NULL COMMENT '公告类型(1通知 2公告)',
  `notice_content` text COMMENT '公告内容',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_notice_uuid` (`uuid`),
  KEY `ix_sys_notice_updated_id` (`updated_id`),
  KEY `ix_sys_notice_updated_time` (`updated_time`),
  KEY `ix_sys_notice_is_deleted` (`is_deleted`),
  KEY `ix_sys_notice_status` (`status`),
  KEY `ix_sys_notice_deleted_id` (`deleted_id`),
  KEY `ix_sys_notice_created_time` (`created_time`),
  KEY `ix_sys_notice_deleted_time` (`deleted_time`),
  KEY `ix_sys_notice_id` (`id`),
  KEY `ix_sys_notice_created_id` (`created_id`),
  CONSTRAINT `sys_notice_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_notice_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_notice_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='通知公告表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_param`
--

DROP TABLE IF EXISTS `sys_param`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_param` (
  `config_name` varchar(64) NOT NULL COMMENT '参数名称',
  `config_key` varchar(500) NOT NULL COMMENT '参数键名',
  `config_value` varchar(500) DEFAULT NULL COMMENT '参数键值',
  `config_type` tinyint(1) DEFAULT NULL COMMENT '系统内置(True:是 False:否)',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_param_uuid` (`uuid`),
  KEY `ix_sys_param_id` (`id`),
  KEY `ix_sys_param_updated_time` (`updated_time`),
  KEY `ix_sys_param_is_deleted` (`is_deleted`),
  KEY `ix_sys_param_status` (`status`),
  KEY `ix_sys_param_created_time` (`created_time`),
  KEY `ix_sys_param_deleted_time` (`deleted_time`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='系统参数表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_position`
--

DROP TABLE IF EXISTS `sys_position`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_position` (
  `name` varchar(64) NOT NULL COMMENT '岗位名称',
  `order` int NOT NULL COMMENT '显示排序',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_sys_position_uuid` (`uuid`),
  KEY `ix_sys_position_created_id` (`created_id`),
  KEY `ix_sys_position_updated_id` (`updated_id`),
  KEY `ix_sys_position_updated_time` (`updated_time`),
  KEY `ix_sys_position_id` (`id`),
  KEY `ix_sys_position_is_deleted` (`is_deleted`),
  KEY `ix_sys_position_status` (`status`),
  KEY `ix_sys_position_deleted_id` (`deleted_id`),
  KEY `ix_sys_position_created_time` (`created_time`),
  KEY `ix_sys_position_deleted_time` (`deleted_time`),
  CONSTRAINT `sys_position_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_position_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_position_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='岗位表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role`
--

DROP TABLE IF EXISTS `sys_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role` (
  `name` varchar(64) NOT NULL COMMENT '角色名称',
  `code` varchar(16) NOT NULL COMMENT '角色编码',
  `order` int NOT NULL COMMENT '显示排序',
  `data_scope` int NOT NULL COMMENT '数据权限范围(1:仅本人 2:本部门 3:本部门及以下 4:全部 5:自定义)',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  UNIQUE KEY `ix_sys_role_uuid` (`uuid`),
  KEY `ix_sys_role_id` (`id`),
  KEY `ix_sys_role_is_deleted` (`is_deleted`),
  KEY `ix_sys_role_status` (`status`),
  KEY `ix_sys_role_created_time` (`created_time`),
  KEY `ix_sys_role_deleted_time` (`deleted_time`),
  KEY `ix_sys_role_updated_time` (`updated_time`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='角色表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role_depts`
--

DROP TABLE IF EXISTS `sys_role_depts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role_depts` (
  `role_id` int NOT NULL COMMENT '角色ID',
  `dept_id` int NOT NULL COMMENT '部门ID',
  PRIMARY KEY (`role_id`,`dept_id`),
  KEY `dept_id` (`dept_id`),
  CONSTRAINT `sys_role_depts_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sys_role_depts_ibfk_2` FOREIGN KEY (`dept_id`) REFERENCES `sys_dept` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='角色部门关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_role_menus`
--

DROP TABLE IF EXISTS `sys_role_menus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_role_menus` (
  `role_id` int NOT NULL COMMENT '角色ID',
  `menu_id` int NOT NULL COMMENT '菜单ID',
  PRIMARY KEY (`role_id`,`menu_id`),
  KEY `menu_id` (`menu_id`),
  CONSTRAINT `sys_role_menus_ibfk_1` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sys_role_menus_ibfk_2` FOREIGN KEY (`menu_id`) REFERENCES `sys_menu` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='角色菜单关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_tenant`
--

DROP TABLE IF EXISTS `sys_tenant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_tenant` (
  `name` varchar(100) NOT NULL COMMENT '租户名称',
  `code` varchar(100) NOT NULL COMMENT '租户编码',
  `start_time` datetime DEFAULT NULL COMMENT '开始时间',
  `end_time` datetime DEFAULT NULL COMMENT '结束时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `code` (`code`),
  UNIQUE KEY `ix_sys_tenant_uuid` (`uuid`),
  KEY `ix_sys_tenant_is_deleted` (`is_deleted`),
  KEY `ix_sys_tenant_status` (`status`),
  KEY `ix_sys_tenant_created_time` (`created_time`),
  KEY `ix_sys_tenant_deleted_time` (`deleted_time`),
  KEY `ix_sys_tenant_id` (`id`),
  KEY `ix_sys_tenant_updated_time` (`updated_time`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='租户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user`
--

DROP TABLE IF EXISTS `sys_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user` (
  `username` varchar(64) NOT NULL COMMENT '用户名/登录账号',
  `password` varchar(255) NOT NULL COMMENT '密码哈希',
  `name` varchar(32) NOT NULL COMMENT '昵称',
  `mobile` varchar(11) DEFAULT NULL COMMENT '手机号',
  `email` varchar(64) DEFAULT NULL COMMENT '邮箱',
  `gender` varchar(1) DEFAULT NULL COMMENT '性别(0:男 1:女 2:未知)',
  `avatar` varchar(255) DEFAULT NULL COMMENT '头像URL地址',
  `is_superuser` tinyint(1) NOT NULL COMMENT '是否超管',
  `last_login` datetime DEFAULT NULL COMMENT '最后登录时间',
  `gitee_login` varchar(32) DEFAULT NULL COMMENT 'Gitee登录',
  `github_login` varchar(32) DEFAULT NULL COMMENT 'Github登录',
  `wx_login` varchar(32) DEFAULT NULL COMMENT '微信登录',
  `qq_login` varchar(32) DEFAULT NULL COMMENT 'QQ登录',
  `dept_id` int DEFAULT NULL COMMENT '部门ID',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `tenant_id` int NOT NULL COMMENT '租户ID',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  `id_card` varchar(255) DEFAULT NULL COMMENT '身份证号(SM4加密)',
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `ix_sys_user_uuid` (`uuid`),
  UNIQUE KEY `mobile` (`mobile`),
  UNIQUE KEY `email` (`email`),
  KEY `ix_sys_user_created_time` (`created_time`),
  KEY `ix_sys_user_deleted_time` (`deleted_time`),
  KEY `ix_sys_user_tenant_id` (`tenant_id`),
  KEY `ix_sys_user_deleted_id` (`deleted_id`),
  KEY `ix_sys_user_created_id` (`created_id`),
  KEY `ix_sys_user_updated_time` (`updated_time`),
  KEY `ix_sys_user_dept_id` (`dept_id`),
  KEY `ix_sys_user_updated_id` (`updated_id`),
  KEY `ix_sys_user_status` (`status`),
  KEY `ix_sys_user_id` (`id`),
  KEY `ix_sys_user_is_deleted` (`is_deleted`),
  CONSTRAINT `sys_user_ibfk_1` FOREIGN KEY (`dept_id`) REFERENCES `sys_dept` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_user_ibfk_2` FOREIGN KEY (`tenant_id`) REFERENCES `sys_tenant` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `sys_user_ibfk_3` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_user_ibfk_4` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `sys_user_ibfk_5` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user_positions`
--

DROP TABLE IF EXISTS `sys_user_positions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user_positions` (
  `user_id` int NOT NULL COMMENT '用户ID',
  `position_id` int NOT NULL COMMENT '岗位ID',
  PRIMARY KEY (`user_id`,`position_id`),
  KEY `position_id` (`position_id`),
  CONSTRAINT `sys_user_positions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sys_user_positions_ibfk_2` FOREIGN KEY (`position_id`) REFERENCES `sys_position` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户岗位关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sys_user_roles`
--

DROP TABLE IF EXISTS `sys_user_roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sys_user_roles` (
  `user_id` int NOT NULL COMMENT '用户ID',
  `role_id` int NOT NULL COMMENT '角色ID',
  PRIMARY KEY (`user_id`,`role_id`),
  KEY `role_id` (`role_id`),
  CONSTRAINT `sys_user_roles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `sys_user` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `sys_user_roles_ibfk_2` FOREIGN KEY (`role_id`) REFERENCES `sys_role` (`id`) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户角色关联表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_job`
--

DROP TABLE IF EXISTS `task_job`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_job` (
  `job_id` varchar(64) NOT NULL COMMENT '任务ID',
  `job_name` varchar(128) DEFAULT NULL COMMENT '任务名称',
  `trigger_type` varchar(32) DEFAULT NULL COMMENT '触发方式: cron/interval/date/manual',
  `status` varchar(16) NOT NULL COMMENT '执行状态',
  `next_run_time` varchar(64) DEFAULT NULL COMMENT '下次执行时间',
  `job_state` text COMMENT '任务状态信息',
  `result` text COMMENT '执行结果',
  `error` text COMMENT '错误信息',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_task_job_uuid` (`uuid`),
  KEY `ix_task_job_deleted_time` (`deleted_time`),
  KEY `ix_task_job_created_time` (`created_time`),
  KEY `ix_task_job_is_deleted` (`is_deleted`),
  KEY `ix_task_job_job_id` (`job_id`),
  KEY `ix_task_job_updated_time` (`updated_time`),
  KEY `ix_task_job_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='任务执行日志表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_node`
--

DROP TABLE IF EXISTS `task_node`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_node` (
  `name` varchar(64) NOT NULL COMMENT '节点名称',
  `code` varchar(32) NOT NULL COMMENT '节点编码',
  `jobstore` varchar(64) DEFAULT NULL COMMENT '存储器',
  `executor` varchar(64) DEFAULT NULL COMMENT '执行器',
  `trigger` varchar(64) DEFAULT NULL COMMENT '触发器',
  `trigger_args` text COMMENT '触发器参数',
  `func` text COMMENT '代码块',
  `args` text COMMENT '位置参数',
  `kwargs` text COMMENT '关键字参数',
  `coalesce` tinyint(1) DEFAULT NULL COMMENT '是否合并运行',
  `max_instances` int DEFAULT NULL COMMENT '最大实例数',
  `start_date` varchar(64) DEFAULT NULL COMMENT '开始时间',
  `end_date` varchar(64) DEFAULT NULL COMMENT '结束时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  UNIQUE KEY `ix_task_node_uuid` (`uuid`),
  KEY `ix_task_node_updated_id` (`updated_id`),
  KEY `ix_task_node_id` (`id`),
  KEY `ix_task_node_updated_time` (`updated_time`),
  KEY `ix_task_node_is_deleted` (`is_deleted`),
  KEY `ix_task_node_status` (`status`),
  KEY `ix_task_node_deleted_id` (`deleted_id`),
  KEY `ix_task_node_created_time` (`created_time`),
  KEY `ix_task_node_deleted_time` (`deleted_time`),
  KEY `ix_task_node_created_id` (`created_id`),
  CONSTRAINT `task_node_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_node_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_node_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='节点类型表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_workflow`
--

DROP TABLE IF EXISTS `task_workflow`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_workflow` (
  `name` varchar(128) NOT NULL COMMENT '流程名称',
  `code` varchar(64) NOT NULL COMMENT '流程编码',
  `workflow_status` varchar(32) NOT NULL COMMENT '流程状态: draft/published/archived',
  `nodes` json DEFAULT NULL COMMENT 'Vue Flow nodes JSON',
  `edges` json DEFAULT NULL COMMENT 'Vue Flow edges JSON',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_task_workflow_code` (`code`),
  UNIQUE KEY `ix_task_workflow_uuid` (`uuid`),
  KEY `ix_task_workflow_id` (`id`),
  KEY `ix_task_workflow_updated_id` (`updated_id`),
  KEY `ix_task_workflow_is_deleted` (`is_deleted`),
  KEY `ix_task_workflow_created_time` (`created_time`),
  KEY `ix_task_workflow_updated_time` (`updated_time`),
  KEY `ix_task_workflow_deleted_time` (`deleted_time`),
  KEY `ix_task_workflow_status` (`status`),
  KEY `ix_task_workflow_created_id` (`created_id`),
  KEY `ix_task_workflow_deleted_id` (`deleted_id`),
  CONSTRAINT `task_workflow_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_workflow_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_workflow_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流定义表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_workflow_node_type`
--

DROP TABLE IF EXISTS `task_workflow_node_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_workflow_node_type` (
  `name` varchar(128) NOT NULL COMMENT '显示名称',
  `code` varchar(64) NOT NULL COMMENT '节点编码，对应画布 node.type',
  `category` varchar(32) NOT NULL COMMENT '分类: trigger/action/condition/control',
  `func` text NOT NULL COMMENT 'Python 代码块，须定义 handler(*args,**kwargs)',
  `args` text COMMENT '默认位置参数，逗号分隔',
  `kwargs` text COMMENT '默认关键字参数 JSON',
  `sort_order` int NOT NULL COMMENT '排序',
  `is_active` tinyint(1) NOT NULL COMMENT '是否启用',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uuid` varchar(64) NOT NULL COMMENT 'UUID全局唯一标识',
  `status` varchar(10) NOT NULL COMMENT '状态(0:正常 1:禁用)',
  `description` text COMMENT '备注/描述',
  `created_time` datetime NOT NULL COMMENT '创建时间',
  `updated_time` datetime NOT NULL COMMENT '更新时间',
  `is_deleted` tinyint(1) NOT NULL COMMENT '是否已删除(0:未删除 1:已删除)',
  `deleted_time` datetime DEFAULT NULL COMMENT '删除时间',
  `created_id` int DEFAULT NULL COMMENT '创建人ID',
  `updated_id` int DEFAULT NULL COMMENT '更新人ID',
  `deleted_id` int DEFAULT NULL COMMENT '删除人ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  UNIQUE KEY `ix_task_workflow_node_type_uuid` (`uuid`),
  KEY `ix_task_workflow_node_type_updated_time` (`updated_time`),
  KEY `ix_task_workflow_node_type_created_id` (`created_id`),
  KEY `ix_task_workflow_node_type_status` (`status`),
  KEY `ix_task_workflow_node_type_updated_id` (`updated_id`),
  KEY `ix_task_workflow_node_type_id` (`id`),
  KEY `ix_task_workflow_node_type_deleted_id` (`deleted_id`),
  KEY `ix_task_workflow_node_type_is_deleted` (`is_deleted`),
  KEY `ix_task_workflow_node_type_deleted_time` (`deleted_time`),
  KEY `ix_task_workflow_node_type_created_time` (`created_time`),
  CONSTRAINT `task_workflow_node_type_ibfk_1` FOREIGN KEY (`created_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_workflow_node_type_ibfk_2` FOREIGN KEY (`updated_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `task_workflow_node_type_ibfk_3` FOREIGN KEY (`deleted_id`) REFERENCES `sys_user` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='工作流编排节点类型（非定时任务节点）';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'fastapiadmin'
--

--
-- Dumping routines for database 'fastapiadmin'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-27 16:05:54
