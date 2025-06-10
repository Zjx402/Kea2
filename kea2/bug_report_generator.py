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
    Generate HTML format bug reports
    """

    def __init__(self, result_dir):
        """
        Initialize the bug report generator

        Args:
            result_dir: Directory path containing test results
        """
        self.result_dir = Path(result_dir)
        self.log_timestamp = self.result_dir.name.split("_", 1)[1]
        self.screenshots_dir = self.result_dir / f"output_{self.log_timestamp}" / "screenshots"
        self.take_screenshots = self._detect_screenshots_setting()
        
        # Set up Jinja2 environment
        # First try to load templates from the package
        try:
            self.jinja_env = Environment(
                loader=PackageLoader("kea2", "templates"),
                autoescape=select_autoescape(['html', 'xml'])
            )
        except (ImportError, ValueError):
            # If unable to load from package, load from current directory's templates folder
            current_dir = Path(__file__).parent
            templates_dir = current_dir / "templates"
            
            # Ensure template directory exists
            if not templates_dir.exists():
                templates_dir.mkdir(parents=True, exist_ok=True)
                
            self.jinja_env = Environment(
                loader=FileSystemLoader(templates_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            
            # If template file doesn't exist, it will be created on first report generation

    def generate_report(self):
        """
        Generate bug report and save to result directory
        """
        try:
            logger.debug("Starting bug report generation")

            # Collect test data
            test_data = self._collect_test_data()

            # Generate HTML report
            html_content = self._generate_html_report(test_data)

            # Save report
            report_path = self.result_dir / "bug_report.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.debug(f"Bug report generated: {report_path}")

        except Exception as e:
            logger.error(f"Error generating bug report: {e}")

    def _collect_test_data(self):
        """
        Collect test data, including results, coverage, etc.
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
            "screenshot_info": {},  # Store detailed information for each screenshot
            "coverage_trend": []  # Store coverage trend data
        }

        # Get screenshot count
        if self.screenshots_dir.exists():
            screenshots = sorted(self.screenshots_dir.glob("screenshot-*.png"),
                                 key=lambda x: int(x.name.split("-")[1].split(".")[0]))
            data["screenshots_count"] = len(screenshots)

        # Parse steps.log file to get test step numbers and screenshot mappings
        steps_log_path = self.result_dir / f"output_{self.log_timestamp}" / "steps.log"
        property_violations = {}  # Store multiple violation records for each property: {property_name: [{start, end, screenshot}, ...]}
        start_screenshot = None  # Screenshot name at the start of testing
        fail_screenshot = None  # Screenshot name at test failure
        
        # For storing time data
        first_precond_time = None  # Time of the first ScriptInfo entry with state=start
        first_fail_time = None     # Time of the first ScriptInfo entry with state=fail

        if steps_log_path.exists():
            with open(steps_log_path, "r", encoding="utf-8") as f:
                # First read all steps
                steps = []
                
                for line in f:
                    try:
                        step_data = json.loads(line)
                        steps.append(step_data)
                        
                        # Extract time from ScriptInfo entries
                        if step_data.get("Type") == "ScriptInfo":
                            try:
                                info = json.loads(step_data.get("Info", "{}")) if isinstance(step_data.get("Info"), str) else step_data.get("Info", {})
                                state = info.get("state", "")
                                
                                # Record the first ScriptInfo with state=start as precondition time
                                if state == "start" and first_precond_time is None:
                                    first_precond_time = step_data.get("Time")
                                
                                # Record the first ScriptInfo with state=fail as fail time
                                elif state == "fail" and first_fail_time is None:
                                    first_fail_time = step_data.get("Time")
                            except Exception as e:
                                logger.error(f"Error parsing ScriptInfo: {e}")
                    except:
                        pass

                # Calculate number of Monkey events
                monkey_events_count = sum(1 for step in steps if step.get("Type") == "Monkey")
                data["executed_events"] = monkey_events_count

                # Track current test state
                current_property = None
                current_test = {}

                # Collect detailed information for each screenshot
                for step in steps:
                    step_type = step.get("Type", "")
                    screenshot = step.get("Screenshot", "")
                    info = step.get("Info", "{}")

                    if screenshot and screenshot not in data["screenshot_info"]:
                        try:
                            info_obj = json.loads(info) if isinstance(info, str) else info
                            caption = ""

                            if step_type == "Monkey":
                                # Extract 'act' attribute for Monkey type and convert to lowercase
                                caption = f"{info_obj.get('act', 'N/A').lower()}"
                            elif step_type == "Script":
                                # Extract 'method' attribute for Script type
                                caption = f"{info_obj.get('method', 'N/A')}"
                            elif step_type == "ScriptInfo":
                                # Extract 'propName' and 'state' attributes for ScriptInfo type
                                prop_name = info_obj.get('propName', '')
                                state = info_obj.get('state', 'N/A')
                                caption = f"{prop_name} {state}" if prop_name else f"{state}"

                            data["screenshot_info"][screenshot] = {
                                "type": step_type,
                                "caption": caption
                            }
                        except Exception as e:
                            logger.error(f"Error parsing screenshot info: {e}")
                            data["screenshot_info"][screenshot] = {
                                "type": step_type,
                                "caption": step_type
                            }

                # Find start and end step numbers and corresponding screenshots for all tests
                for i, step in enumerate(steps, 1):  # Start counting from 1 to match screenshot numbering
                    if step.get("Type") == "ScriptInfo":
                        try:
                            info = json.loads(step.get("Info", "{}"))
                            property_name = info.get("propName", "")
                            state = info.get("state", "")
                            screenshot = step.get("Screenshot", "")

                            if property_name and state:
                                if state == "start":
                                    # Record new test start
                                    current_property = property_name
                                    current_test = {
                                        "start": i,
                                        "end": None,
                                        "screenshot_start": screenshot
                                    }
                                    # Record screenshot at test start
                                    if not start_screenshot and screenshot:
                                        start_screenshot = screenshot

                                elif state == "fail" or state == "pass":
                                    if current_property == property_name:
                                        # Update test end information
                                        current_test["end"] = i
                                        current_test["screenshot_end"] = screenshot

                                        if state == "fail":
                                            # Record failed test
                                            if property_name not in property_violations:
                                                property_violations[property_name] = []

                                            property_violations[property_name].append({
                                                "start": current_test["start"],
                                                "end": current_test["end"],
                                                "screenshot_start": current_test["screenshot_start"],
                                                "screenshot_end": screenshot
                                            })

                                            # Record screenshot at test failure
                                            if not fail_screenshot and screenshot:
                                                fail_screenshot = screenshot

                                        # Reset current test
                                        current_property = None
                                        current_test = {}
                        except:
                            pass
        
        # Calculate test time
        start_time = None
        
        # Parse fastbot log file to get start time
        fastbot_log_path = list(self.result_dir.glob("fastbot_*.log"))
        if fastbot_log_path:
            try:
                with open(fastbot_log_path[0], "r", encoding="utf-8") as f:
                    log_content = f.read()

                    # Extract test start time
                    start_match = re.search(r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]  @Version',
                                            log_content)
                    if start_match:
                        start_time_str = start_match.group(1)
                        start_time = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    
                    # Extract test end time (last timestamp)
                    end_matches = re.findall(r'\[Fastbot\]\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3})\]',
                                         log_content)
                    end_time = None
                    if end_matches:
                        end_time_str = end_matches[-1]
                        end_time = datetime.datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S.%f")
                    
                    # Calculate total test time (in seconds)
                    if start_time and end_time:
                        data["total_testing_time"] = int((end_time - start_time).total_seconds())
            except Exception as e:
                logger.error(f"Error parsing fastbot log file: {e}")
                logger.error(f"Error details: {str(e)}")
        
        # Calculate first_bug_time and first_precondition_time from steps.log data
        if start_time:
            # If first_precond_time exists, calculate first_precondition_time
            if first_precond_time:
                try:
                    precond_time = datetime.datetime.strptime(first_precond_time, "%Y-%m-%d %H:%M:%S.%f")
                    data["first_precondition_time"] = int((precond_time - start_time).total_seconds())
                except Exception as e:
                    logger.error(f"Error parsing precond_time: {e}")
            
            # If first_fail_time exists, calculate first_bug_time
            if first_fail_time:
                try:
                    fail_time = datetime.datetime.strptime(first_fail_time, "%Y-%m-%d %H:%M:%S.%f")
                    data["first_bug_time"] = int((fail_time - start_time).total_seconds())
                except Exception as e:
                    logger.error(f"Error parsing fail_time: {e}")

        # Parse result file
        result_json_path = list(self.result_dir.glob("result_*.json"))
        property_stats = {}  # Store property names and corresponding statistics

        if result_json_path:
            with open(result_json_path[0], "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Calculate bug count and get property names
            for property_name, test_result in result_data.items():
                # Extract property name (last part of test name)

                # Initialize property statistics
                if property_name not in property_stats:
                    property_stats[property_name] = {
                        "precond_satisfied": 0,
                        "precond_checked": 0,
                        "postcond_violated": 0,
                        "error": 0
                    }

                # Extract statistics directly from result_*.json file
                property_stats[property_name]["precond_satisfied"] += test_result.get("precond_satisfied", 0)
                property_stats[property_name]["precond_checked"] += test_result.get("executed", 0)
                property_stats[property_name]["postcond_violated"] += test_result.get("fail", 0)
                property_stats[property_name]["error"] += test_result.get("error", 0)

                # Check if failed or error
                if test_result.get("fail", 0) > 0 or test_result.get("error", 0) > 0:
                    data["bugs_found"] += 1

                data["preconditions_satisfied"] += test_result.get("precond_satisfied", 0)
                # data["executed_events"] += test_result.get("executed", 0)

        # Parse coverage data
        coverage_log_path = self.result_dir / f"output_{self.log_timestamp}" / "coverage.log"
        if coverage_log_path.exists():
            with open(coverage_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    # Collect coverage trend data
                    for line in lines:
                        try:
                            coverage_data = json.loads(line)
                            data["coverage_trend"].append({
                                "steps": coverage_data.get("stepsCount", 0),
                                "coverage": coverage_data.get("coverage", 0),
                                "tested_activities_count": len(coverage_data.get("testedActivities", []))
                            })
                        except Exception as e:
                            logger.error(f"Error parsing coverage data: {e}")
                            continue
                    
                    # Ensure sorted by steps
                    data["coverage_trend"].sort(key=lambda x: x["steps"])
                    
                    try:
                        # Read last line to get final coverage data
                        coverage_data = json.loads(lines[-1])
                        data["coverage"] = coverage_data.get("coverage", 0)
                        data["total_activities"] = coverage_data.get("totalActivities", [])
                        data["tested_activities"] = coverage_data.get("testedActivities", [])
                    except Exception as e:
                        logger.error(f"Error parsing final coverage data: {e}")

        # Generate Property Violations list
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

        # Generate Property Stats list
        if property_stats:
            index = 1
            for property_name, stats in property_stats.items():
                data["property_stats"].append({
                    "index": index,
                    "property_name": property_name,
                    "precond_satisfied": stats["precond_satisfied"],
                    "precond_checked": stats["precond_checked"],
                    "postcond_violated": stats["postcond_violated"],
                    "error": stats["error"]
                })
                index += 1

        return data

    def _detect_screenshots_setting(self):
        """
        Detect if screenshots were enabled during test run.
        Returns True if screenshots were taken, False otherwise.
        """
        # Method 1: Check if screenshots directory exists and has content
        if self.screenshots_dir.exists() and any(self.screenshots_dir.glob("screenshot-*.png")):
            return True
            
        # Method 2: Try to read init config from logs
        fastbot_log_path = list(self.result_dir.glob("fastbot_*.log"))
        if fastbot_log_path:
            try:
                with open(fastbot_log_path[0], "r", encoding="utf-8") as f:
                    log_content = f.read()
                    if '"takeScreenshots": true' in log_content:
                        return True
            except Exception:
                pass
                
        return False

    def _generate_html_report(self, data):
        """
        Generate HTML format bug report
        """
        try:
            # Prepare screenshot data
            screenshots = []
            relative_path = f"output_{self.log_timestamp}/screenshots"

            if self.screenshots_dir.exists():
                screenshot_files = sorted(self.screenshots_dir.glob("screenshot-*.png"),
                                     key=lambda x: int(x.name.split("-")[1].split(".")[0]))

                for i, screenshot in enumerate(screenshot_files, 1):
                    screenshot_name = screenshot.name

                    # Get information for this screenshot
                    caption = f"{i}"
                    if screenshot_name in data["screenshot_info"]:
                        info = data["screenshot_info"][screenshot_name]
                        caption = f"{i}. {info.get('caption', '')}"

                    screenshots.append({
                        'id': i,
                        'path': f"{relative_path}/{screenshot_name}",
                        'caption': caption
                    })
            
            # Format timestamp for display
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Ensure coverage_trend has data
            if not data["coverage_trend"]:
                logger.warning("No coverage trend data")
                data["coverage_trend"] = [{"steps": 0, "coverage": 0, "tested_activities_count": 0}]
            
            # Convert coverage_trend to JSON string, ensuring all data points are included
            coverage_trend_json = json.dumps(data["coverage_trend"])
            logger.debug(f"Number of coverage trend data points: {len(data['coverage_trend'])}")
            
            # Prepare template data
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
                'tested_activities': data["tested_activities"],  # Pass list of tested Activities
                'total_activities': data["total_activities"],    # Pass list of all Activities
                'items_per_page': 10,  # Items to display per page
                'screenshots': screenshots,
                'property_violations': data["property_violations"],
                'property_stats': data["property_stats"],
                'coverage_data': coverage_trend_json,
                'take_screenshots': self.take_screenshots  # Pass screenshot setting to template
            }
            
            # Check if template exists, if not create it
            template_path = Path(__file__).parent / "templates" / "bug_report_template.html"
            if not template_path.exists():
                logger.warning("Template file does not exist, creating default template...")
            
            # Use Jinja2 to render template
            template = self.jinja_env.get_template("bug_report_template.html")
            html_content = template.render(**template_data)
            
            return html_content
            
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            raise