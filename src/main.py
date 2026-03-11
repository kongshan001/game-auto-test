"""
游戏自动化测试框架主程序
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional

# 添加src目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import Config
from utils.glm_client import GLMClient
from game.game_launcher import GameLauncher
from action.window_manager import WindowManager
from vision.screen_capture import ScreenCapture
from vision.ocr_engine import OCREngine
from vision.element_locator import ElementLocator
from action.input_executor import ActionExecutor
from agents.decision_agent import DecisionAgent
from agents.state_memory import StateMemory


# 配置日志
def setup_logging(log_level: str = "INFO"):
    # 确保日志目录存在
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/test.log', encoding='utf-8')
        ]
    )


class GameAutoTester:
    """游戏自动化测试器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 初始化各模块
        self.glm_client = GLMClient(
            api_key=config.glm_api_key,
            model=config.glm_model
        )
        
        self.game_launcher = GameLauncher(
            exe_path=config.game_exe_path,
            window_title=config.game_window_title,
            startup_delay=config.game_startup_delay
        )
        
        self.window_manager = WindowManager()
        self.screen_capture = ScreenCapture(save_path=config.screenshot_save_path)
        
        self.ocr_engine = OCREngine(
            languages=config.ocr_languages,
            use_gpu=False
        ) if config.ocr_enabled else None
        
        self.element_locator = ElementLocator(
            ocr_engine=self.ocr_engine,
            glm_client=self.glm_client
        )
        
        self.action_executor = ActionExecutor(
            click_delay=config.click_delay,
            type_delay=config.type_delay,
            keypress_delay=config.keypress_delay
        )
        
        self.state_memory = StateMemory()
        self.state_memory.set_test_case(config.test_case)
        
        self.window_info = None
        self.running = False
        
    def initialize(self):
        """初始化测试环境"""
        self.logger.info("开始初始化测试环境...")
        
        # 启动游戏
        self.logger.info(f"启动游戏: {self.config.game_exe_path}")
        self.game_launcher.launch()
        
        # 等待窗口出现
        self.logger.info("等待游戏窗口...")
        self.window_info = self.window_manager.wait_for_window(
            self.game_launcher.process,
            timeout=30,
            title=self.config.game_window_title
        )
        
        if not self.window_info:
            raise RuntimeError("无法获取游戏窗口")
        
        # 配置各模块的窗口信息
        self.screen_capture.set_window(self.window_info)
        self.element_locator.window_info = self.window_info
        self.action_executor.window_info = self.window_info
        
        # 激活窗口
        self.window_manager.activate_window(self.window_info.hwnd)
        
        # 初始化决策Agent
        self.decision_agent = DecisionAgent(
            glm_client=self.glm_client,
            test_case=self.config.test_case,
            state_memory=self.state_memory
        )
        
        self.logger.info(f"游戏窗口: {self.window_info.title}")
        self.logger.info(f"窗口大小: {self.window_info.width}x{self.window_info.height}")
        
        # 开始测试
        self.state_memory.start_test()
        self.running = True
        
    def execute_action(self, action: dict) -> bool:
        """执行动作"""
        action_type = action.get("action")
        
        try:
            if action_type == "click":
                target = action.get("target")
                screenshot = self.screen_capture.capture()
                success = self.action_executor.click(
                    target=target,
                    image=screenshot,
                    locator=self.element_locator
                )
                self.state_memory.add_action(
                    action="click",
                    target=str(target),
                    description=action.get("description", ""),
                    success=success
                )
                return success
                
            elif action_type == "type":
                target = action.get("target")
                text = action.get("text", "")
                screenshot = self.screen_capture.capture()
                success = self.action_executor.type_text(
                    text=text,
                    target=target,
                    image=screenshot,
                    locator=self.element_locator
                )
                self.state_memory.add_action(
                    action="type",
                    target=str(target),
                    description=f"输入: {text}",
                    success=success
                )
                return success
                
            elif action_type == "keypress":
                key = action.get("key")
                success = self.action_executor.press_key(key)
                self.state_memory.add_action(
                    action="keypress",
                    target=key,
                    description=f"按下{key}",
                    success=success
                )
                return success
                
            elif action_type == "wait":
                seconds = action.get("seconds", 1)
                self.action_executor.wait(seconds)
                self.state_memory.add_action(
                    action="wait",
                    target=str(seconds),
                    description=f"等待{seconds}秒",
                    success=True
                )
                return True
                
            elif action_type == "assert":
                # 验证条件
                condition = action.get("condition", "")
                screenshot = self.screen_capture.capture()
                
                # 使用OCR检查文本是否存在
                if self.ocr_engine:
                    matches = self.ocr_engine.search_text(screenshot, condition)
                    success = len(matches) > 0
                else:
                    # OCR未启用时抛出警告
                    self.logger.warning("OCR未启用，无法执行断言验证")
                    success = False
                
                self.state_memory.add_action(
                    action="assert",
                    target=condition,
                    description=f"验证: {condition}",
                    success=success
                )
                return success
                
            elif action_type == "done":
                success = action.get("success", True)
                reason = action.get("reason", "")
                self.state_memory.add_action(
                    action="done",
                    target="",
                    description=f"测试完成: {reason}",
                    success=success
                )
                return success
                
            else:
                self.logger.warning(f"未知动作类型: {action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"执行动作失败: {e}")
            self.state_memory.add_action(
                action=action_type or "unknown",
                target="",
                description=str(e),
                success=False,
                error=str(e)
            )
            return False
    
    def run(self):
        """运行测试"""
        try:
            self.initialize()
            
            step = 0
            max_steps = self.config.max_steps
            
            while self.running and step < max_steps:
                step += 1
                self.logger.info(f"\n{'='*50}")
                self.logger.info(f"步骤 {step}/{max_steps}")
                self.logger.info(f"{'='*50}")
                
                # 捕获当前画面
                screenshot = self.screen_capture.capture()
                
                # 保存截图
                if self.config.save_screenshots:
                    self.screen_capture.capture_and_save(
                        step=step,
                        action="before"
                    )
                
                # 获取场景描述（可选，用于减少token）
                scene_description = None
                
                # 决策下一步动作
                action = self.decision_agent.decide(
                    image=screenshot,
                    scene_description=scene_description
                )
                
                self.logger.info(f"决策动作: {action}")
                
                # 验证动作格式
                if not self.decision_agent.validate_action(action):
                    self.logger.warning(f"动作格式无效: {action}")
                    action = {"action": "wait", "seconds": 1}
                
                # 执行动作
                success = self.execute_action(action)
                
                # 保存截图
                if self.config.save_screenshots:
                    self.screen_capture.capture_and_save(
                        step=step,
                        action=action.get("action", "unknown")
                    )
                
                # 检查是否完成
                if action.get("action") == "done":
                    self.logger.info(f"测试完成: {action.get('reason', '')}")
                    self.running = False
                    self.state_memory.end_test(success=action.get("success", True))
                    break
                
                # 检查动作是否失败
                if not success:
                    self.logger.warning("动作执行失败，可能需要重试")
                
                # 短暂等待让画面更新
                time.sleep(1)
            
            # 超时检查
            if step >= max_steps:
                self.logger.warning("达到最大步骤数，测试结束")
                self.state_memory.end_test(success=False)
                
        except KeyboardInterrupt:
            self.logger.info("用户中断测试")
            self.state_memory.end_test(success=False)
        except Exception as e:
            self.logger.error(f"测试出错: {e}")
            self.state_memory.end_test(success=False)
            raise
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        self.logger.info("清理资源...")
        
        # 保存测试记录
        self.state_memory.save_to_file("logs/test_record.json")
        
        # 显示测试摘要
        summary = self.state_memory.get_summary()
        self.logger.info(f"测试摘要: {summary}")
        
        # 关闭游戏
        if self.game_launcher.is_running():
            self.logger.info("关闭游戏...")
            self.game_launcher.close(force=True)
        
        # 关闭GLM客户端
        if hasattr(self.glm_client, 'close'):
            self.glm_client.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Windows游戏自动化测试框架")
    parser.add_argument("--config", "-c", default=".env", help="配置文件路径")
    args = parser.parse_args()
    
    # 加载配置
    config = Config.from_env(args.config)
    config.validate()
    
    # 配置日志
    setup_logging(config.log_level)
    
    # 创建测试器并运行
    tester = GameAutoTester(config)
    tester.run()


if __name__ == "__main__":
    main()
