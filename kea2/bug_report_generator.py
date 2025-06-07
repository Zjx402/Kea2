import os
import json
import datetime
import re
from pathlib import Path
import shutil
from jinja2 import Environment, FileSystemLoader, select_autoescape, PackageLoader
from .utils import getLogger

logger = getLogger(__name__)


class BugReportGenerator:
    """
    用于生成HTML格式的bug报告
    """

    def __init__(self, result_dir):
        """
        初始化bug报告生成器

        Args:
            result_dir: 包含测试结果的目录路径
        """
        self.result_dir = Path(result_dir)
        self.log_timestamp = self.result_dir.name.split("_", 1)[1]
        self.screenshots_dir = self.result_dir / f"output_{self.log_timestamp}" / "screenshots"
        
        # 设置Jinja2环境
        # 首先尝试从包内加载模板
        try:
            self.jinja_env = Environment(
                loader=PackageLoader("kea2", "templates"),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except (ImportError, ValueError):
            # 如果无法从包加载，则从当前目录的templates文件夹加载
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"
            
            # 确保模板目录存在
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                
            self.jinja_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            
            # 如果模板文件不存在，我们将在第一次生成报告时创建它

    def generate_report(self):
        """
        生成bug报告并保存到结果目录
        """
        try:
            logger.debug("开始生成bug报告")

            # 收集测试数据
            test_data = self._collect_test_data()

            # 生成HTML报告
            html_content = self._generate_html_report(test_data)

            # 保存报告
            report_path = self.result_dir / "bug_report_template.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.debug(f"Bug报告已生成: {report_path}")

        except Exception as e:
            logger.error(f"生成bug报告时出错: {e}")

    def _collect_test_data(self):
        """
        收集测试数据，包括结果、覆盖率等
        """
        data = {
            "timestamp": self.log_timestamp,
            "bugs_found": 0,
            "preconditions_satisfied": 0,
            "executed_events": 0,
            "total_testing_time": 0,
            "first_bug_time": 0,
            "first_precondition_time": 0,
            "coverage": 0,
            "total_activities": [],
            "tested_activities": [],
            "property_violations": [],
            "property_stats": [],
            "screenshots_count": 0,
            "screenshot_info": {},  # 用于存储每个截图的详细信息
            "coverage_trend": []  # 用于存储覆盖率变化趋势
        }

        # 获取截图数量
        if self.screenshots_dir.exists():
            screenshots = sorted(self.screenshots_dir.glob("screenshot-*.png"),
                                 key=lambda x: int(x.name.split("-")[1].split(".")[0]))
            data["screenshots_count"] = len(screenshots)

        # 解析steps.log文件获取测试步骤序号和截图对应关系
        steps_log_path = self.result_dir / f"output_{self.log_timestamp}" / "steps.log"
        property_violations = {}  # 存储每个属性的多次违规记录: {property_name: [{start, end, screenshot}, ...]}
        start_screenshot = None  # 开始测试时的截图名称
        fail_screenshot = None  # 测试失败时的截图名称

        if steps_log_path.exists():
            with open(steps_log_path, "r", encoding="utf-8") as f:
                # 首先读取所有步骤
                steps = []
                for line in f:
                    try:
                        steps.append(json.loads(line))
                    except:
                        pass

                # 计算Monkey事件数量
                monkey_events_count = sum(1 for step in steps if step.get("Type") == "Monkey")
                data["executed_events"] = monkey_events_count

                # 跟踪当前测试的状态
                current_property = None
                current_test = {}

                # 收集每个截图的详细信息
                for step in steps:
                    step_type = step.get("Type", "")
                    screenshot = step.get("Screenshot", "")
                    info = step.get("Info", "{}")

                    if screenshot and screenshot not in data["screenshot_info"]:
                        try:
                            info_obj = json.loads(info) if isinstance(info, str) else info
                            caption = ""

                            if step_type == "Monkey":
                                # 提取Monkey类型的act属性，并转换为小写
                                caption = f"{info_obj.get('act', 'N/A').lower()}"
                            elif step_type == "Script":
                                # 提取Script类型的method属性
                                caption = f"{info_obj.get('method', 'N/A')}"
                            elif step_type == "ScriptInfo":
                                # 提取ScriptInfo类型的state属性
                                caption = f"{info_obj.get('state', 'N/A')}"

                            data["screenshot_info"][screenshot] = {
                                "type": step_type,
                                "caption": caption
                            }
                        except Exception as e:
                            logger.error(f"解析截图信息时出错: {e}")
                            data["screenshot_info"][screenshot] = {
                                "type": step_type,
                                "caption": step_type
                            }

                # 查找所有测试的开始和结束步骤序号以及对应的截图
                for i, step in enumerate(steps, 1):  # 从1开始计数，与截图编号对应
                    if step.get("Type") == "ScriptInfo":
                        try:
                            info = json.loads(step.get("Info", "{}"))
                            prop_name = info.get("propName", "")
                            state = info.get("state", "")
                            screenshot = step.get("Screenshot", "")

                            if prop_name and state:
                                # 提取测试名称的最后部分作为属性名
                                property_name = prop_name.split(".")[-1]

                                if state == "start":
                                    # 记录新测试的开始
                                    current_property = property_name
                                    current_test = {
                                        "start": i,
                                        "end": None,
                                        "screenshot_start": screenshot
                                    }
                                    # 记录开始测试时的截图
                                    if not start_screenshot and screenshot:
                                        start_screenshot = screenshot

                                elif state == "fail" or state == "pass":
                                    if current_property == property_name:
                                        # 更新测试结束信息
                                        current_test["end"] = i
                                        current_test["screenshot_end"] = screenshot

                                        if state == "fail":
                                            # 记录失败的测试
                                            if property_name not in property_violations:
                                                property_violations[property_name] = []

                                            property_violations[property_name].append({
                                                "start": current_test["start"],
                                                "end": current_test["end"],
                                                "screenshot_start": current_test["screenshot_start"],
                                                "screenshot_end": screenshot
                                            })

                                            # 记录测试失败时的截图
                                            if not fail_screenshot and screenshot:
                                                fail_screenshot = screenshot

                                        # 重置当前测试
                                        current_property = None
                                        current_test = {}
                        except:
                            pass

        # 解析fastbot日志文件以获取时间信息
        fastbot_log_path = list(self.result_dir.glob("fastbot_*.log"))
        if fastbot_log_path:
            try:
                with open(fastbot_log_path[0], "r", encoding="utf-8") as f:
                    log_content = f.read()

                    # 提取测试开始时间
                    start_match = re.search(r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]  @Version',
                                            log_content)
                    start_time = None
                    if start_match:
                        start_time_str = start_match.group(1)
                        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    # 提取测试结束时间（最后一个时间戳）
                    end_matches = re.findall(r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]',
                                             log_content)
                    end_time = None
                    if end_matches:
                        end_time_str = end_matches[-1]
                        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    # 查找测试失败状态的时间戳 ("state":"fail")
                    fail_matches = re.findall(
                        r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\].*\"state\":\"fail\"', log_content)
                    fail_time = None
                    if fail_matches:
                        fail_time_str = fail_matches[0]  # 取第一个失败时间
                        fail_time = datetime.datetime.strptime(fail_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    # 查找测试开始状态的时间戳 ("state":"start")
                    precond_matches = re.findall(
                        r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\].*\"state\":\"start\"',
                        log_content)
                    precond_time = None
                    if precond_matches:
                        precond_time_str = precond_matches[0]  # 取第一个开始时间
                        precond_time = datetime.datetime.strptime(precond_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    # 根据截图名称在日志中确认时间戳
                    if fail_screenshot and not fail_time:
                        timestamp_part = fail_screenshot.split("-")[-1].split(".")[0]
                        fail_log_pattern = re.compile(
                            r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\].*' + timestamp_part)
                        fail_log_match = fail_log_pattern.search(log_content)
                        if fail_log_match:
                            fail_time_str = fail_log_match.group(1)
                            fail_time = datetime.datetime.strptime(fail_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    if start_screenshot and not precond_time:
                        timestamp_part = start_screenshot.split("-")[-1].split(".")[0]
                        precond_log_pattern = re.compile(
                            r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\].*' + timestamp_part)
                        precond_log_match = precond_log_pattern.search(log_content)
                        if precond_log_match:
                            precond_time_str = precond_log_match.group(1)
                            precond_time = datetime.datetime.strptime(precond_time_str, "%Y-%m-%d %H:%M:%S.%f")

                    # 计算时间差（以秒为单位）
                    if start_time and end_time:
                        data["total_testing_time"] = round((end_time - start_time).total_seconds(), 2)

                    if start_time and fail_time:
                        data["first_bug_time"] = round((fail_time - start_time).total_seconds(), 2)

                    if start_time and precond_time:
                        data["first_precondition_time"] = round((precond_time - start_time).total_seconds(), 2)
            except Exception as e:
                logger.error(f"解析fastbot日志文件时出错: {e}")
                logger.error(f"错误详情: {str(e)}")

        # 解析结果文件
        result_json_path = list(self.result_dir.glob("result_*.json"))
        property_stats = {}  # 存储属性名称和对应的统计信息

        if result_json_path:
            with open(result_json_path[0], "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # 计算bug数量并获取属性名称
            for property_name, test_result in result_data.items():
                # 提取属性名称（测试名称的最后部分）

                # 初始化属性统计信息
                if property_name not in property_stats:
                    property_stats[property_name] = {
                        "precond_satisfied": 0,
                        "precond_checked": 0,
                        "postcond_violated": 0,
                        "ui_not_found": 0
                    }

                # 直接从result_*.json文件中提取统计数据
                property_stats[property_name]["precond_satisfied"] += test_result.get("precond_satisfied", 0)
                property_stats[property_name]["precond_checked"] += test_result.get("executed", 0)
                property_stats[property_name]["postcond_violated"] += test_result.get("fail", 0)
                property_stats[property_name]["ui_not_found"] += test_result.get("error", 0)

                # 检查是否失败或错误
                if test_result.get("fail", 0) > 0 or test_result.get("error", 0) > 0:
                    data["bugs_found"] += 1

                data["preconditions_satisfied"] += test_result.get("precond_satisfied", 0)
                # data["executed_events"] += test_result.get("executed", 0)

        # 解析覆盖率数据
        coverage_log_path = self.result_dir / f"output_{self.log_timestamp}" / "coverage.log"
        if coverage_log_path.exists():
            with open(coverage_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    # 收集覆盖率变化趋势
                    for line in lines:
                        try:
                            coverage_data = json.loads(line)
                            data["coverage_trend"].append({
                                "steps": coverage_data.get("stepsCount", 0),
                                "coverage": coverage_data.get("coverage", 0),
                                "tested_activities_count": len(coverage_data.get("testedActivities", []))
                            })
                        except:
                            pass

                    try:
                        # 只读取最后一行
                        coverage_data = json.loads(lines[-1])
                        data["coverage"] = coverage_data.get("coverage", 0)
                        data["total_activities"] = coverage_data.get("totalActivities", [])
                        data["tested_activities"] = coverage_data.get("testedActivities", [])
                    except:
                        pass

        # 生成Property Violations列表
        if property_violations:
            index = 1
            for property_name, violations in property_violations.items():
                for violation in violations:
                    start_step = violation["start"]
                    end_step = violation["end"]
                    data["property_violations"].append({
                        "index": index,
                        "property_name": property_name,
                        "precondition_page": start_step,
                        "interaction_pages": [start_step, end_step],
                        "postcondition_page": end_step
                    })
                    index += 1

        # 生成Property Stats列表
        if property_stats:
            index = 1
            for property_name, stats in property_stats.items():
                data["property_stats"].append({
                    "index": index,
                    "property_name": property_name,
                    "precond_satisfied": stats["precond_satisfied"],
                    "precond_checked": stats["precond_checked"],
                    "postcond_violated": stats["postcond_violated"],
                    "ui_not_found": stats["ui_not_found"]
                })
                index += 1

        return data

    def _generate_html_report(self, data):
        """
        生成HTML格式的bug报告
        """
        try:
            # 准备截图数据
            screenshots = []
            relative_path = f"output_{self.log_timestamp}/screenshots"

            if self.screenshots_dir.exists():
                screenshot_files = sorted(self.screenshots_dir.glob("screenshot-*.png"),
                                     key=lambda x: int(x.name.split("-")[1].split(".")[0]))

                for i, screenshot in enumerate(screenshot_files, 1):
                    screenshot_name = screenshot.name

                    # 获取截图对应的信息
                    caption = f"{i}"
                    if screenshot_name in data["screenshot_info"]:
                        info = data["screenshot_info"][screenshot_name]
                        caption = f"{i}. {info.get('caption', '')}"

                    screenshots.append({
                        'id': i,
                        'path': f"{relative_path}/{screenshot_name}",
                        'caption': caption
                    })
            
            # 格式化时间戳以便显示
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 准备模板数据
            template_data = {
                'timestamp': timestamp,
                'bugs_found': data["bugs_found"],
                'total_testing_time': data["total_testing_time"],
                'executed_events': data["executed_events"],
                'coverage_percent': round(data["coverage"], 2),
                'first_bug_time': data["first_bug_time"],
                'first_precondition_time': data["first_precondition_time"],
                'total_activities_count': len(data["total_activities"]),
                'tested_activities_count': len(data["tested_activities"]),
                'screenshots': screenshots,
                'property_violations': data["property_violations"],
                'property_stats': data["property_stats"],
                'coverage_data': json.dumps(data["coverage_trend"])
            }
            
            # 检查模板是否存在，如果不存在则创建
            template_path = Path(__file__).parent / "templates" / "bug_report_template.html"
            if not template_path.exists():
                logger.warning("模板文件不存在，正在创建默认模板...")
                # 在这种情况下不做任何事情，因为模板文件应该已经创建好了
            
            # 使用Jinja2渲染模板
            template = self.jinja_env.get_template("bug_report_template.html")
            html_content = template.render(**template_data)
            
            return html_content
            
        except Exception as e:
            logger.error(f"渲染模板时出错: {e}")
            raise