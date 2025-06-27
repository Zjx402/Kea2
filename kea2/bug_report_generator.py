import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, TypedDict, List, Deque, NewType
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw
from jinja2 import Environment, FileSystemLoader, select_autoescape, PackageLoader
from kea2.utils import getLogger

logger = getLogger(__name__)


class StepData(TypedDict):
    # The type of the action (Monkey / Script / Script Info)
    Type: str
    # The steps of monkey event when the action happened
    # ps: since we insert script actions into monkey actions. Total actions count >= Monkey actions count
    MonkeyStepsCount: int
    # The time stamp of the action
    Time: str
    # The execution info of the action
    Info: Dict
    # The screenshot of the action
    Screenshot: str


class CovData(TypedDict):
    stepsCount: int  # The MonkeyStepsCount when profiling the Coverage data
    coverage: float
    totalActivitiesCount: int
    testedActivitiesCount: int
    totalActivities: List[str]
    testedActivities: List[str]


class ReportData(TypedDict):
    timestamp: str
    bugs_found: int
    executed_events: int
    total_testing_time: float
    coverage: float
    total_activities_count: int
    tested_activities_count: int
    total_activities: List
    tested_activities: List
    property_violations: List[Dict]
    property_stats: List
    screenshot_info: Dict
    coverage_trend: List


class PropertyExecResult(TypedDict):
    precond_satisfied: int
    executed: int
    fail: int
    error: int


PropertyName = NewType("PropertyName", str)
TestResult = NewType("TestResult", Dict[PropertyName, PropertyExecResult])


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

    _cov_trend: Deque[CovData] = None
    _test_result: TestResult = None
    _take_screenshots: bool = None
    _data_path: DataPath = None

    @property
    def cov_trend(self):
        if self._cov_trend is not None:
            return self._cov_trend

        # Parse coverage data
        if not self.data_path.coverage_log.exists():
            logger.error(f"{self.data_path.coverage_log} not exists")

        cov_trend = list()

        with open(self.data_path.coverage_log, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                coverage_data = json.loads(line)
                cov_trend.append(coverage_data)
        self._cov_trend = cov_trend
        return self._cov_trend

    @property
    def take_screenshots(self) -> bool:
        """Whether the `--take-screenshots` enabled. Should we report the screenshots?

        Returns:
            bool: Whether the `--take-screenshots` enabled.
        """
        if self._take_screenshots is None:
            self._take_screenshots = self.data_path.screenshots_dir.exists()
        return self._take_screenshots

    @property
    def test_result(self) -> TestResult:
        if self._test_result is not None:
            return self._test_result

        if not self.data_path.result_json.exists():
            logger.error(f"{self.data_path.result_json} not found")
        with open(self.data_path.result_json, "r", encoding="utf-8") as f:
            self._test_result: TestResult = json.load(f)

        return self._test_result

    def __init__(self, result_dir=None):
        """
        Initialize the bug report generator

        Args:
            result_dir: Directory path containing test results
        """
        if result_dir is not None:
            self._setup_paths(result_dir)

        self.executor = ThreadPoolExecutor(max_workers=128)

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

    def _setup_paths(self, result_dir):
        """
        Setup paths for a given result directory

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

    def generate_report(self, result_dir_path=None):
        """
        Generate bug report and save to result directory

        Args:
            result_dir_path: Directory path containing test results (optional)
                           If not provided, uses the path from initialization
        """
        try:
            # Setup paths if result_dir_path is provided
            if result_dir_path is not None:
                self._setup_paths(result_dir_path)

            # Check if paths are properly set up
            if not hasattr(self, 'result_dir') or self.result_dir is None:
                raise ValueError(
                    "No result directory specified. Please provide result_dir_path or initialize with a directory.")

            logger.debug("Starting bug report generation")

            # Collect test data
            test_data: ReportData = self._collect_test_data()

            # Generate HTML report
            html_content = self._generate_html_report(test_data)

            # Save report
            report_path = self.result_dir / "bug_report.html"
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.debug(f"Bug report saved to: {report_path}")
            return str(report_path)

        except Exception as e:
            logger.error(f"Error generating bug report: {e}")
            raise
        finally:
            self.executor.shutdown()

    def _collect_test_data(self) -> ReportData:
        """
        Collect test data, including results, coverage, etc.
        """
        data: ReportData = {
            "timestamp": self.log_timestamp,
            "bugs_found": 0,
            "executed_events": 0,
            "total_testing_time": 0,
            "coverage": 0,
            "total_activities": [],
            "tested_activities": [],
            "property_violations": [],
            "property_stats": [],
            "screenshot_info": {},  # Store detailed information for each screenshot
            "coverage_trend": []  # Store coverage trend data
        }

        # Parse steps.log file to get test step numbers and screenshot mappings
        property_violations = {}  # Store multiple violation records for each property

        if not self.data_path.steps_log.exists():
            logger.error(f"{self.data_path.steps_log} not exists")
            return

        current_property = None
        current_test = {}
        step_index = 0
        monkey_events_count = 0  # Track monkey events separately

        with open(self.data_path.steps_log, "r", encoding="utf-8") as f:
            # Track current test state

            for step_index, line in enumerate(f, start=1):
                step_data = self._parse_step_data(line)

                if not step_data:
                    continue

                step_type = step_data.get("Type", "")
                screenshot = step_data.get("Screenshot", "")
                info = step_data.get("Info", {})

                # Count Monkey events separately
                if step_type == "Monkey":
                    monkey_events_count += 1

                # If screenshots are enabled, mark the screenshot
                if self.take_screenshots and step_data["Screenshot"]:
                    self.executor.submit(self._mark_screenshot, step_data)

                # Collect detailed information for each screenshot
                if screenshot and screenshot not in data["screenshot_info"]:
                    self._add_screenshot_info(step_data, step_index, data)

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

            # Set the monkey events count correctly
            data["executed_events"] = monkey_events_count

            # Calculate test time
            if first_step_time and last_step_time:
                def _get_datetime(raw_datetime) -> datetime:
                    return datetime.strptime(raw_datetime, r"%Y-%m-%d %H:%M:%S.%f")

                test_time = _get_datetime(last_step_time) - _get_datetime(first_step_time)

                total_seconds = int(test_time.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                data["total_testing_time"] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        # Calculate bug count directly from result data
        for property_name, test_result in self.test_result.items():
            # Check if failed or error
            if test_result["fail"] > 0 or test_result["error"] > 0:
                data["bugs_found"] += 1

        # Store the raw result data for direct use in HTML template
        data["property_stats"] = self.test_result

        # Process coverage data
        data["coverage_trend"] = self.cov_trend

        if self.cov_trend:
            final_trend = self.cov_trend[-1]
            data["coverage"] = final_trend["coverage"]
            data["total_activities"] = final_trend["totalActivities"]
            data["tested_activities"] = final_trend["testedActivities"]
            data["total_activities_count"] = final_trend["totalActivitiesCount"]
            data["tested_activities_count"] = final_trend["testedActivitiesCount"]

        # Generate Property Violations list
        self._generate_property_violations_list(property_violations, data)

        return data

    def _parse_step_data(self, raw_step_info: str) -> StepData:
        step_data: StepData = json.loads(raw_step_info)
        step_data["Info"] = json.loads(step_data["Info"])
        return step_data

    def _mark_screenshot(self, step_data: StepData):
        if step_data["Type"] == "Monkey":
            try:
                act = step_data["Info"].get("act")
                pos = step_data["Info"].get("pos")
                if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                    screenshot_name = step_data["Screenshot"]
                    if not screenshot_name:
                        return

                    self._mark_screenshot_interaction(screenshot_name, act, pos)
            except Exception as e:
                logger.error(f"Error when marking screenshots: {e}")

    def _mark_screenshot_interaction(self, screenshot_name: str, action_type: str, position: str):
        """
            Mark interaction on screenshot with colored rectangle

            Args:
                screenshot_name (str): Name of the screenshot file
                action_type (str): Type of action ('CLICK' or 'LONG_CLICK' or 'SCROLL')
                position (list): Position coordinates [x1, y1, x2, y2]

            Returns:
                bool: True if marking was successful, False otherwise
        """
        screenshot_path: Path = self.data_path.screenshots_dir / screenshot_name
        if not screenshot_path.exists():
            logger.error(f"Screenshot file {screenshot_path} not exists.")

        img = Image.open(screenshot_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        if not isinstance(position, (list, tuple)) or len(position) != 4:
            logger.warning(f"Invalid position format: {position}. Skip drawing {screenshot_path}.")
            return

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

    def _generate_html_report(self, data: ReportData):
        """
        Generate HTML format bug report
        """
        try:
            # Format timestamp for display
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Ensure coverage_trend has data
            if not data["coverage_trend"]:
                logger.warning("No coverage trend data")
                # Use the same field names as in coverage.log file
                data["coverage_trend"] = [{"stepsCount": 0, "coverage": 0, "testedActivitiesCount": 0}]

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
                'total_activities_count': data["total_activities_count"],
                'tested_activities_count': data["tested_activities_count"],
                'tested_activities': data["tested_activities"],
                'total_activities': data["total_activities"],
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

    def _add_screenshot_info(self, step_data: StepData, step_index: int, data: Dict):
        """
        Add screenshot information to data structure

        Args:
            step_data: data for the current step
            step_index: Current step index
            data: Data dictionary to update
        """
        caption = ""

        if step_data["Type"] == "Monkey":
            # Extract 'act' attribute for Monkey type and convert to lowercase
            caption = f"{step_data['Info'].get('act', 'N/A')}"
        elif step_data["Type"] == "Script":
            # Extract 'method' attribute for Script type
            caption = f"{step_data['Info'].get('method', 'N/A')}"
        elif step_data["Type"] == "ScriptInfo":
            # Extract 'propName' and 'state' attributes for ScriptInfo type
            prop_name = step_data["Info"].get('propName', '')
            state = step_data["Info"].get('state', 'N/A')
            caption = f"{prop_name}: {state}" if prop_name else f"{state}"

        screenshot_name = step_data["Screenshot"]
        # Use relative path string instead of Path object
        relative_screenshot_path = f"output_{self.log_timestamp}/screenshots/{screenshot_name}"

        data["screenshot_info"][screenshot_name] = {
            "type": step_data["Type"],
            "caption": caption,
            "step_index": step_index
        }

        self.screenshots.append({
            'id': step_index,
            'path': relative_screenshot_path,  # Now using string path
            'caption': f"{step_index}. {caption}"
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


if __name__ == "__main__":
    print("Generating bug report")
    # OUTPUT_PATH = "<Your output path>"
    OUTPUT_PATH = "P:/Python/Kea2/output/res_2025062717_1853221914"

    report_generator = BugReportGenerator()
    report_path = report_generator.generate_report(OUTPUT_PATH)
    print(f"bug report generated: {report_path}")