#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
配置文件修复工具

用于清理配置文件中的旧字段，确保统一配置格式
"""

import json
import os
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("config_fixer")

CONFIG_FILE = "config.json"

def fix_config():
    """修复配置文件"""
    logger.info("开始修复配置文件...")
    
    # 检查配置文件是否存在
    if not os.path.exists(CONFIG_FILE):
        logger.warning(f"配置文件 {CONFIG_FILE} 不存在，无需修复")
        return
    
    try:
        # 读取现有配置
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            
        logger.info("加载现有配置成功")
        
        # 检查并更新global_hotkeys部分
        if "global_hotkeys" not in config:
            logger.warning("配置中没有global_hotkeys部分，将创建")
            config["global_hotkeys"] = {}
            
        # 将window_search中的快捷键移动到global_hotkeys
        if "window_search" in config:
            # 保存快捷键相关配置并从window_search中移除
            keys_to_remove = ["hotkey", "prev_window_hotkey", "next_window_hotkey"]
            
            if "hotkey" in config["window_search"] and config["window_search"]["hotkey"]:
                # 确保search键在global_hotkeys中
                if not config["global_hotkeys"].get("search"):
                    config["global_hotkeys"]["search"] = config["window_search"]["hotkey"]
                    logger.info(f"将window_search.hotkey设置为global_hotkeys.search: {config['window_search']['hotkey']}")
                    
            if "prev_window_hotkey" in config["window_search"] and config["window_search"]["prev_window_hotkey"]:
                # 确保prev_window键在global_hotkeys中
                if not config["global_hotkeys"].get("prev_window"):
                    config["global_hotkeys"]["prev_window"] = config["window_search"]["prev_window_hotkey"]
                    logger.info(f"将window_search.prev_window_hotkey设置为global_hotkeys.prev_window: {config['window_search']['prev_window_hotkey']}")
                    
            if "next_window_hotkey" in config["window_search"] and config["window_search"]["next_window_hotkey"]:
                # 确保next_window键在global_hotkeys中
                if not config["global_hotkeys"].get("next_window"):
                    config["global_hotkeys"]["next_window"] = config["window_search"]["next_window_hotkey"]
                    logger.info(f"将window_search.next_window_hotkey设置为global_hotkeys.next_window: {config['window_search']['next_window_hotkey']}")
            
            # 从window_search中移除快捷键相关配置
            for key in keys_to_remove:
                if key in config["window_search"]:
                    del config["window_search"][key]
                    logger.info(f"从window_search中移除{key}")
        
        # 修复window_search.window_search的问题
        if "global_hotkeys" in config and "window_search" in config["global_hotkeys"]:
            if not config["global_hotkeys"].get("search"):
                config["global_hotkeys"]["search"] = config["global_hotkeys"]["window_search"]
                logger.info(f"将global_hotkeys.window_search改名为global_hotkeys.search: {config['global_hotkeys']['window_search']}")
            del config["global_hotkeys"]["window_search"]
            logger.info("从global_hotkeys中移除window_search")
                
        # 保存修复后的配置
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
            
        logger.info("配置文件修复完成")
        
    except Exception as e:
        logger.error(f"修复配置文件时出错: {str(e)}", exc_info=True)
        
if __name__ == "__main__":
    fix_config() 