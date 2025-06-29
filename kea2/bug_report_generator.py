import json
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, TypedDict, List, Deque, NewType, Union
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw, ImageFont
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
    all_properties_count: int
    executed_properties_count: int
    property_violations: List[Dict]
    property_stats: List
    property_error_details: Dict[str, List[Dict]]  # Support multiple errors per property
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
    property_exec_info: Path


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
            screenshots_dir=self.result_dir / f"output_{self.log_timestamp}" / "screenshots",
            property_exec_info=self.result_dir / f"property_exec_info_{self.log_timestamp}.json"
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
            "all_properties_count": 0,
            "executed_properties_count": 0,
            "property_violations": [],
            "property_stats": [],
            "property_error_details": {},
            "screenshot_info": {},
            "coverage_trend": []
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

        # Calculate properties statistics
        data["all_properties_count"] = len(self.test_result)
        data["executed_properties_count"] = sum(1 for result in self.test_result.values() if result.get("executed", 0) > 0)

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

        # Load error details for properties with fail/error state
        data["property_error_details"] = self._load_property_error_details()

        return data

    def _parse_step_data(self, raw_step_info: str) -> StepData:
        step_data: StepData = json.loads(raw_step_info)
        step_data["Info"] = json.loads(step_data["Info"])
        return step_data

    def _mark_screenshot(self, step_data: StepData):
        try:
            step_type = step_data["Type"]
            screenshot_name = step_data["Screenshot"]
            if not screenshot_name:
                return

            if step_type == "Monkey":
                act = step_data["Info"].get("act")
                pos = step_data["Info"].get("pos")
                if act in ["CLICK", "LONG_CLICK"] or act.startswith("SCROLL"):
                    self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)

            elif step_type == "Script":
                act = step_data["Info"].get("method")
                pos = step_data["Info"].get("params")
                if act in ["click", "setText", "swipe"]:
                    self._mark_screenshot_interaction(step_type, screenshot_name, act, pos)

        except Exception as e:
            logger.error(f"Error when marking screenshots: {e}")


    def _mark_screenshot_interaction(self, step_type: str, screenshot_name: str, action_type: str, position: Union[List, tuple]) -> bool:
        """
            Mark interaction on screenshot with colored rectangle

            Args:
                step_type (str): Type of the step (Monkey or Script)
                screenshot_name (str): Name of the screenshot file
                action_type (str): Type of action (CLICK/LONG_CLICK/SCROLL for Monkey, click/setText/swipe for Script)
                position: Position coordinates or parameters (format varies by action type)

            Returns:
                bool: True if marking was successful, False otherwise
        """
        screenshot_path: Path = self.data_path.screenshots_dir / screenshot_name
        if not screenshot_path.exists():
            logger.error(f"Screenshot file {screenshot_path} not exists.")
            return False

        img = Image.open(screenshot_path).convert("RGB")
        draw = ImageDraw.Draw(img)
        line_width = 5

        if step_type == "Monkey":
            if len(position) < 4:
                logger.warning(f"Monkey action requires 4 coordinates, got {len(position)}. Skip drawing.")
                return False

            x1, y1, x2, y2 = map(int, position[:4])

            if action_type == "CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(255, 0, 0))
            elif action_type == "LONG_CLICK":
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 0, 255))
            elif action_type.startswith("SCROLL"):
                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(0, 255, 0))

        elif step_type == "Script":
            if action_type == "click":

                if len(position) < 2:
                    logger.warning(f"Script click action requires 2 coordinates, got {len(position)}. Skip drawing.")
                    return False
                
                x, y = map(float, position[:2])
                x1, y1, x2, y2 = x - 50, y - 50, x + 50, y + 50

                for i in range(line_width):
                    draw.rectangle([x1 - i, y1 - i, x2 + i, y2 + i], outline=(255, 0, 0))
                    
            elif action_type == "swipe":

                if len(position) < 4:
                    logger.warning(f"Script swipe action requires 4 coordinates, got {len(position)}. Skip drawing.")
                    return False
                
                x1, y1, x2, y2 = map(float, position[:4])
                
                # mark start and end positions with rectangles
                start_x1, start_y1, start_x2, start_y2 = x1 - 50, y1 - 50, x1 + 50, y1 + 50
                for i in range(line_width):
                    draw.rectangle([start_x1 - i, start_y1 - i, start_x2 + i, start_y2 + i], outline=(255, 0, 0))

                end_x1, end_y1, end_x2, end_y2 = x2 - 50, y2 - 50, x2 + 50, y2 + 50
                for i in range(line_width):
                    draw.rectangle([end_x1 - i, end_y1 - i, end_x2 + i, end_y2 + i], outline=(255, 0, 0))
                
                # draw line between start and end positions
                draw.line([(x1, y1), (x2, y2)], fill=(255, 0, 0), width=line_width)
                
                # add text labels for start and end positions
                font = ImageFont.truetype("arial.ttf", 80)
                    
                # draw "start" at start position
                draw.text((x1 - 20, y1 - 70), "start", fill=(255, 0, 0), font=font)
                    
                # draw "end" at end position
                draw.text((x2 - 15, y2 - 70), "end", fill=(255, 0, 0), font=font)

        img.save(screenshot_path)
        return True

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
                'all_properties_count': data["all_properties_count"],
                'executed_properties_count': data["executed_properties_count"],
                'items_per_page': 10,  # Items to display per page
                'screenshots': self.screenshots,
                'property_violations': data["property_violations"],
                'property_stats': data["property_stats"],
                'property_error_details': data["property_error_details"],
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

    def _load_property_error_details(self) -> Dict[str, List[Dict]]:
        """
        Load property execution error details from property_exec_info file
        
        Returns:
            Dict[str, List[Dict]]: Mapping of property names to their error tracebacks with context
        """
        error_details = {}
        
        if not self.data_path.property_exec_info.exists():
            logger.warning(f"Property exec info file {self.data_path.property_exec_info} not found")
            return error_details
            
        try:
            with open(self.data_path.property_exec_info, "r", encoding="utf-8") as f:
                # Use hash map for efficient deduplication
                error_hash_map = {}  # property_name -> {error_hash: error_data}
                
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        exec_info = json.loads(line)
                        prop_name = exec_info.get("propName", "")
                        state = exec_info.get("state", "")
                        tb = exec_info.get("tb", "")
                        
                        # Only process error details for failed or error states
                        if prop_name and state in ["fail", "error"] and tb:
                            if prop_name not in error_hash_map:
                                error_hash_map[prop_name] = {}
                            
                            # Create hash key for this specific error (state + traceback)
                            error_hash = hash((state, tb))
                            
                            if error_hash in error_hash_map[prop_name]:
                                # Error already exists, increment count
                                error_hash_map[prop_name][error_hash]["occurrence_count"] += 1
                            else:
                                # New error, create entry
                                short_desc = self._extract_error_summary(tb)
                                error_hash_map[prop_name][error_hash] = {
                                    "state": state,
                                    "traceback": tb,
                                    "occurrence_count": 1,
                                    "short_description": short_desc
                                }
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse property exec info line {line_number}: {line[:100]}... Error: {e}")
                        continue
                        
                # Convert hash map to list format for template compatibility
                for prop_name, hash_dict in error_hash_map.items():
                    error_details[prop_name] = list(hash_dict.values())
                    # Sort by occurrence count (descending) to show most frequent errors first
                    error_details[prop_name].sort(key=lambda x: x["occurrence_count"], reverse=True)
                        
        except Exception as e:
            logger.error(f"Error reading property exec info file: {e}")
            
        return error_details

    def _extract_error_summary(self, traceback: str) -> str:
        """
        Extract a short error summary from the full traceback
        
        Args:
            traceback: Full error traceback string
            
        Returns:
            str: Short error summary
        """
        try:
            lines = traceback.strip().split('\n')

            for line in reversed(lines):
                line = line.strip()
                if line and not line.startswith('  '):
                    return line
            return "Unknown error"
        except Exception:
            return "Error parsing traceback"


if __name__ == "__main__":
    print("Generating bug report")
    # OUTPUT_PATH = "<Your output path>"
    OUTPUT_PATH = "P:/Python/Kea2/output/res_2025062921_4535312225"

    report_generator = BugReportGenerator()
    report_path = report_generator.generate_report(OUTPUT_PATH)
    print(f"bug report generated: {report_path}")