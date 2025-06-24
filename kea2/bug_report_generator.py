import json
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, TypedDict, Literal, List
from collections import deque

from PIL import Image, ImageDraw
from jinja2 import Environment, FileSystemLoader, select_autoescape, PackageLoader
from .utils import getLogger


logger = getLogger(__name__)


class StepData(TypedDict):
    Type: str
    MonkeyStepsCount: int
    Time: str
    Info: Dict
    Screenshot: str

@dataclass
class DataPath:
    steps_log: Path
    result_json: Path
    coverage_log: Path
    screenshots_dir: Path


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

        self.data_path: DataPath = DataPath(
            steps_log=self.result_dir / f"output_{self.log_timestamp}" / "steps.log",
            result_json=self.result_dir / f"result_{self.log_timestamp}.json",
            coverage_log=self.result_dir / f"output_{self.log_timestamp}" / "coverage.log",
            screenshots_dir=self.result_dir / f"output_{self.log_timestamp}" / "screenshots"
        )

        self.screenshots = deque()

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

            logger.debug(f"Bug report saved to: {report_path}")

        except Exception as e:
            logger.error(f"Error generating bug report: {e}")

    def _collect_test_data(self):
        """
        Collect test data, including results, coverage, etc.
        """
        data = {
            "timestamp": self.log_timestamp,
            "bugs_found": 0,
            "executed_events": 0,
            "total_testing_time": 0,
            "first_bug_time": 0,
            "first_precondition_time": 0,
            "coverage": 0,
            "total_activities": [],
            "tested_activities": [],
            "property_violations": [],
            "property_stats": [],
            "screenshot_info": {},  # Store detailed information for each screenshot
            "coverage_trend": []  # Store coverage trend data
        }

        # Parse steps.log file to get test step numbers and screenshot mappings
        steps_log_path = self.data_path.steps_log
        property_violations = {}  # Store multiple violation records for each property
        relative_path = f"output_{self.log_timestamp}/screenshots"

        if steps_log_path.exists():
            with open(steps_log_path, "r", encoding="utf-8") as f:
                # Track current test state
                current_property = None
                current_test = {}
                monkey_events_count = 0
                step_index = 0

                for line in f:
                    step_data = self._parse_step_data(line)
                    if step_data:
                        step_index += 1  # Count steps starting from 1
                        step_type = step_data.get("Type", "")
                        screenshot = step_data.get("Screenshot", "")
                        info = step_data.get("Info", {})

                        # Count Monkey events
                        if step_type == "Monkey":
                            monkey_events_count += 1

                        # If screenshots are enabled, mark the screenshot
                        if self.take_screenshots and screenshot:
                            self._mark_screenshot(step_data)

                        # Collect detailed information for each screenshot
                        if screenshot and screenshot not in data["screenshot_info"]:
                            self._add_screenshot_info(screenshot, step_type, info, step_index, relative_path, data)

                        # Process ScriptInfo for property violations
                        if step_type == "ScriptInfo":
                            try:
                                property_name = info.get("propName", "")
                                state = info.get("state", "")
                                current_property, current_test = self._process_script_info(
                                    property_name, state, step_index, screenshot,
                                    current_property, current_test, property_violations
                                )
                            except Exception as e:
                                logger.error(f"Error processing ScriptInfo step {step_index}: {e}")

                        # Store first and last step for time calculation
                        if step_index == 1:
                            first_step_time = step_data["Time"]
                        last_step_time = step_data["Time"]

                # Set the monkey events count
                data["executed_events"] = monkey_events_count

                # Calculate test time
                if step_index > 0:
                    try:
                        data["total_testing_time"] = int((datetime.datetime.strptime(last_step_time,"%Y-%m-%d %H:%M:%S.%f") -
                                                          datetime.datetime.strptime(first_step_time,"%Y-%m-%d %H:%M:%S.%f")
                                                         ).total_seconds())
                    except Exception as e:
                        logger.error(f"Error calculating test time: {e}")

        # Parse result file
        result_json_path = self.data_path.result_json
        
        if result_json_path.exists():
            with open(result_json_path, "r", encoding="utf-8") as f:
                result_data = json.load(f)

            # Calculate bug count directly from result data
            for property_name, test_result in result_data.items():
                # Check if failed or error
                if test_result.get("fail", 0) > 0 or test_result.get("error", 0) > 0:
                    data["bugs_found"] += 1

            # Store the raw result data for direct use in HTML template
            data["property_stats"] = result_data

        # Process coverage data
        cov_trend, last_line = self._get_cov_trend()
        if cov_trend:
            data["coverage_trend"] = cov_trend

        if last_line:
            try:
                coverage_data = json.loads(last_line)
                if coverage_data:
                    data["coverage"] = coverage_data.get("coverage", 0)
                    data["total_activities"] = coverage_data.get("totalActivities", [])
                    data["tested_activities"] = coverage_data.get("testedActivities", [])
            except Exception as e:
                logger.error(f"Error parsing final coverage data: {e}")

        # Generate Property Violations list
        self._generate_property_violations_list(property_violations, data)

        return data

    def _parse_step_data(self, raw_step_info: str) -> StepData:
        step_data = json.loads(raw_step_info)
        step_data["Info"] = json.loads(step_data.get("Info"))
        return step_data

    def _mark_screenshot(self, step_data: StepData):
        if step_data["Type"] == "Monkey":
            try:
                act = step_data["Info"].get("act")
                pos = step_data["Info"].get("pos")
                screenshot_name = step_data["Screenshot"]
                if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                    screenshot_path = self.data_path.screenshots_dir / screenshot_name
                    if screenshot_path.exists():
                        self._mark_screenshot_interaction(screenshot_path, act, pos)
            except Exception as e:
                logger.error(f"Error processing Monkey step: {e}")


    def _mark_screenshot_interaction(self, screenshot_path, action_type, position):
        """
            Mark interaction on screenshot with colored rectangle

            Args:
                screenshot_path (Path): Path to the screenshot file
                action_type (str): Type of action ('CLICK' or 'LONG_CLICK' or 'SCROLL')
                position (list): Position coordinates [x1, y1, x2, y2]

            Returns:
                bool: True if marking was successful, False otherwise
        """
        try:
            img = Image.open(screenshot_path).convert("RGB")
            draw = ImageDraw.Draw(img)

            if not isinstance(position, (list, tuple)) or len(position) != 4:
                logger.warning(f"Invalid position format: {position}")
                return False

            x1, y1, x2, y2 = map(int, position)

            line_width = 5

            if action_type == "CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(255, 0, 0))
            elif action_type == "LONG_CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 0, 255))
            elif action_type.startswith("SCROLL"):
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 255, 0))

            img.save(screenshot_path)
            return True

        except Exception as e:
            logger.error(f"Error marking screenshot {screenshot_path}: {e}")
            return False


    def _detect_screenshots_setting(self):
        """
            Detect if screenshots were enabled during test run.
            Returns True if screenshots were taken, False otherwise.
        """
        return self.data_path.screenshots_dir.exists()

    def _get_cov_trend(self):
        # Parse coverage data
        coverage_log_path = self.data_path.coverage_log
        cov_trend = []
        last_line = None
        if coverage_log_path.exists():
            with open(coverage_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        coverage_data = json.loads(line)
                        cov_trend.append({
                            "steps": coverage_data.get("stepsCount", 0),
                            "coverage": coverage_data.get("coverage", 0),
                            "tested_activities_count": coverage_data.get("testedActivitiesCount", 0)
                        })
                        last_line = line
                    except Exception as e:
                        logger.error(f"Error parsing coverage data: {e}")
                        continue
        return cov_trend, last_line

    def _generate_html_report(self, data):
        """
        Generate HTML format bug report
        """
        try:
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
                'total_activities': data["total_activities"],  # Pass list of all Activities
                'items_per_page': 10,  # Items to display per page
                'screenshots': self.screenshots,
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

    def _add_screenshot_info(self, screenshot: str, step_type: str, info: Dict, step_index: int, relative_path: str, data: Dict):
        """
        Add screenshot information to data structure
        
        Args:
            screenshot: Screenshot filename
            step_type: Type of step (Monkey, Script, ScriptInfo)
            info: Step information dictionary
            step_index: Current step index
            relative_path: Relative path to screenshots directory
            data: Data dictionary to update
        """
        try:
            caption = ""

            if step_type == "Monkey":
                # Extract 'act' attribute for Monkey type and convert to lowercase
                caption = f"{info.get('act', 'N/A').lower()}"
            elif step_type == "Script":
                # Extract 'method' attribute for Script type
                caption = f"{info.get('method', 'N/A')}"
            elif step_type == "ScriptInfo":
                # Extract 'propName' and 'state' attributes for ScriptInfo type
                prop_name = info.get('propName', '')
                state = info.get('state', 'N/A')
                caption = f"{prop_name} {state}" if prop_name else f"{state}"

            data["screenshot_info"][screenshot] = {
                "type": step_type,
                "caption": caption,
                "step_index": step_index
            }
            
            screenshot_caption = data["screenshot_info"][screenshot].get('caption', '')
            self.screenshots.append({
                'id': step_index,
                'path': f"{relative_path}/{screenshot}",
                'caption': f"{step_index}. {screenshot_caption}"
            })
            
        except Exception as e:
            logger.error(f"Error parsing screenshot info: {e}")
            data["screenshot_info"][screenshot] = {
                "type": step_type,
                "caption": step_type,
                "step_index": step_index
            }
            
            screenshot_caption = data["screenshot_info"][screenshot].get('caption', '')
            self.screenshots.append({
                'id': step_index,
                'path': f"{relative_path}/{screenshot}",
                'caption': f"{step_index}. {screenshot_caption}"
            })

    def _process_script_info(self, property_name: str, state: str, step_index: int, screenshot: str, 
                           current_property: str, current_test: Dict, property_violations: Dict) -> tuple:
        """
        Process ScriptInfo step for property violations tracking
        
        Args:
            property_name: Property name from ScriptInfo
            state: State from ScriptInfo (start, pass, fail, error)
            step_index: Current step index
            screenshot: Screenshot filename
            current_property: Currently tracked property
            current_test: Current test data
            property_violations: Dictionary to store violations
            
        Returns:
            tuple: (updated_current_property, updated_current_test)
        """
        if property_name and state:
            if state == "start":
                # Record new test start
                current_property = property_name
                current_test = {
                    "start": step_index,
                    "end": None,
                    "screenshot_start": screenshot
                }

            elif state in ["pass", "fail", "error"]:
                if current_property == property_name:
                    # Update test end information
                    current_test["end"] = step_index
                    current_test["screenshot_end"] = screenshot

                    if state == "fail" or state == "error":
                        # Record failed/error test
                        if property_name not in property_violations:
                            property_violations[property_name] = []

                        property_violations[property_name].append({
                            "start": current_test["start"],
                            "end": current_test["end"],
                            "screenshot_start": current_test["screenshot_start"],
                            "screenshot_end": screenshot
                        })

                    # Reset current test
                    current_property = None
                    current_test = {}
        
        return current_property, current_test

    def _generate_property_violations_list(self, property_violations: Dict, data: Dict):
        """
        Generate property violations list from collected violation data
        
        Args:
            property_violations: Dictionary containing property violations
            data: Data dictionary to update with property violations list
        """
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
