import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import defaultdict

from kea2.utils import getLogger

logger = getLogger(__name__)


class TestReportMerger:
    """
    Merge multiple test result directories into a single combined dataset
    Only processes result_*.json and coverage.log files for the simplified template
    """
    
    def __init__(self):
        self.merged_data = {}
        self.result_dirs = []
        
    def merge_reports(self, result_paths: List[Union[str, Path]], output_dir: Optional[Union[str, Path]] = None) -> Path:
        """
        Merge multiple test result directories
        
        Args:
            result_paths: List of paths to test result directories (res_* directories)
            output_dir: Output directory for merged data (optional)
            
        Returns:
            Path to the merged data directory
        """
        try:
            # Convert paths and validate
            self.result_dirs = [Path(p).resolve() for p in result_paths]
            self._validate_result_dirs()
            
            # Setup output directory
            if output_dir is None:
                timestamp = datetime.now().strftime("%Y%m%d%H_%M%S")
                output_dir = Path.cwd() / f"merged_report_{timestamp}"
            else:
                output_dir = Path(output_dir).resolve()
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            logger.debug(f"Merging {len(self.result_dirs)} test result directories...")
            
            # Merge different types of data
            merged_property_stats = self._merge_property_results()
            merged_coverage_data = self._merge_coverage_data()
            
            # Calculate final statistics
            final_data = self._calculate_final_statistics(merged_property_stats, merged_coverage_data)
            
            # Generate HTML report
            report_file = self._generate_html_report(final_data, output_dir)
            
            # Generate summary
            summary_file = self._generate_summary_report(output_dir)
            
            logger.debug(f"Reports generated successfully in: {output_dir}")
            return output_dir
            
        except Exception as e:
            logger.error(f"Error merging test reports: {e}")
            raise
    
    def _validate_result_dirs(self):
        """Validate that all result directories exist and contain required files"""
        for result_dir in self.result_dirs:
            if not result_dir.exists():
                raise FileNotFoundError(f"Result directory does not exist: {result_dir}")
            
            # Check for required files pattern
            result_files = list(result_dir.glob("result_*.json"))
            if not result_files:
                raise FileNotFoundError(f"No result_*.json file found in: {result_dir}")
            
            logger.debug(f"Validated result directory: {result_dir}")
    
    def _merge_property_results(self) -> Dict[str, Dict]:
        """
        Merge property test results from all directories
        
        Returns:
            Merged property execution results
        """
        merged_results = defaultdict(lambda: {
            "precond_satisfied": 0,
            "executed": 0,
            "fail": 0,
            "error": 0
        })
        
        for result_dir in self.result_dirs:
            result_files = list(result_dir.glob("result_*.json"))
            if not result_files:
                logger.warning(f"No result file found in {result_dir}")
                continue
                
            result_file = result_files[0]  # Take the first (should be only one)
            
            try:
                with open(result_file, 'r', encoding='utf-8') as f:
                    test_results = json.load(f)
                
                # Merge results for each property
                for prop_name, prop_result in test_results.items():
                    for key in ["precond_satisfied", "executed", "fail", "error"]:
                        merged_results[prop_name][key] += prop_result.get(key, 0)
                
                logger.debug(f"Merged results from: {result_file}")
                
            except Exception as e:
                logger.error(f"Error reading result file {result_file}: {e}")
                continue
        
        return dict(merged_results)
    
    def _merge_coverage_data(self) -> Dict:
        """
        Merge coverage data from all directories
        
        Returns:
            Final merged coverage information
        """
        all_activities = set()
        tested_activities = set()
        activity_counts = defaultdict(int)
        total_steps = 0
        
        for result_dir in self.result_dirs:
            # Find coverage log file
            output_dirs = list(result_dir.glob("output_*"))
            if not output_dirs:
                logger.warning(f"No output directory found in {result_dir}")
                continue
                
            coverage_file = output_dirs[0] / "coverage.log"
            if not coverage_file.exists():
                logger.warning(f"No coverage.log found in {output_dirs[0]}")
                continue
            
            try:
                # Read the last line of coverage.log to get final state
                last_coverage = None
                with open(coverage_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            last_coverage = json.loads(line)
                
                if last_coverage:
                    # Collect all activities
                    all_activities.update(last_coverage.get("totalActivities", []))
                    tested_activities.update(last_coverage.get("testedActivities", []))
                    
                    # Update activity counts (take maximum)
                    for activity, count in last_coverage.get("activityCountHistory", {}).items():
                        activity_counts[activity] += count
                    
                    # Add steps count
                    total_steps += last_coverage.get("stepsCount", 0)
                
                logger.debug(f"Merged coverage data from: {coverage_file}")
                
            except Exception as e:
                logger.error(f"Error reading coverage file {coverage_file}: {e}")
                continue
        
        # Calculate final coverage percentage (rounded to 2 decimal places)
        coverage_percent = round((len(tested_activities) / len(all_activities) * 100), 2) if all_activities else 0.00
        
        return {
            "coverage_percent": coverage_percent,
            "total_activities": list(all_activities),
            "tested_activities": list(tested_activities),
            "total_activities_count": len(all_activities),
            "activity_count_history": dict(activity_counts),
            "total_steps": total_steps
        }
    
    def _calculate_final_statistics(self, property_stats: Dict, coverage_data: Dict) -> Dict:
        """
        Calculate final statistics for template rendering
        
        Args:
            property_stats: Merged property statistics
            coverage_data: Merged coverage data
            
        Returns:
            Complete data for template rendering
        """
        # Calculate bug count
        bugs_found = sum(1 for result in property_stats.values() 
                        if result.get('fail', 0) > 0 or result.get('error', 0) > 0)
        
        # Calculate property counts
        all_properties_count = len(property_stats)
        executed_properties_count = sum(1 for result in property_stats.values() 
                                      if result.get('executed', 0) > 0)
        
        # Prepare final data
        final_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'bugs_found': bugs_found,
            'all_properties_count': all_properties_count,
            'executed_properties_count': executed_properties_count,
            'property_stats': property_stats,
            **coverage_data  # Include all coverage data
        }
        
        return final_data
    
    def get_merge_summary(self) -> Dict:
        """
        Get summary of the merge operation
        
        Returns:
            Dictionary containing merge summary information
        """
        if not self.result_dirs:
            return {}
        
        return {
            "merged_directories": len(self.result_dirs),
            "source_paths": [str(p) for p in self.result_dirs],
            "merge_timestamp": datetime.now().isoformat()
        }

    def _generate_html_report(self, data: Dict, output_dir: Path) -> str:
        """
        Generate HTML report using the merged template

        Args:
            data: Final merged data
            output_dir: Output directory

        Returns:
            Path to the generated HTML report
        """
        try:
            from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

            # Set up Jinja2 environment
            try:
                jinja_env = Environment(
                    loader=PackageLoader("kea2", "templates"),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            except (ImportError, ValueError):
                # Fallback to file system loader
                current_dir = Path(__file__).parent
                templates_dir = current_dir / "templates"

                jinja_env = Environment(
                    loader=FileSystemLoader(templates_dir),
                    autoescape=select_autoescape(['html', 'xml'])
                )

            # Render template
            template = jinja_env.get_template("merged_bug_report_template.html")
            html_content = template.render(**data)

            # Save HTML report
            report_file = output_dir / "merged_report.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.debug(f"HTML report generated: {report_file}")
            return str(report_file)

        except Exception as e:
            logger.error(f"Error generating HTML report: {e}")
            raise

    def _generate_summary_report(self, output_dir: Path) -> str:
        """
        Generate a summary report showing merge information

        Args:
            output_dir: Output directory

        Returns:
            Path to the summary report
        """
        try:
            # Create summary data
            summary_data = {
                'merge_timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'source_count': len(self.result_dirs),
                'source_directories': [str(Path(d).name) for d in self.result_dirs],
                'merged_data_location': str(output_dir)
            }

            # Generate summary HTML
            summary_html = self._generate_summary_html(summary_data)

            # Save summary report
            summary_file = output_dir / "merge_summary.html"
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_html)

            logger.debug(f"Merge summary report generated: {summary_file}")
            return str(summary_file)

        except Exception as e:
            logger.error(f"Error generating merge summary report: {e}")
            raise

    def _generate_summary_html(self, summary_data: Dict) -> str:
        """
        Generate HTML content for merge summary using Jinja2 template

        Args:
            summary_data: Summary information

        Returns:
            HTML content string
        """
        try:
            from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape

            # Set up Jinja2 environment (reuse the same setup as _generate_html_report)
            try:
                jinja_env = Environment(
                    loader=PackageLoader("kea2", "templates"),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            except (ImportError, ValueError):
                # Fallback to file system loader
                current_dir = Path(__file__).parent
                templates_dir = current_dir / "templates"

                jinja_env = Environment(
                    loader=FileSystemLoader(templates_dir),
                    autoescape=select_autoescape(['html', 'xml'])
                )

            # Load and render the template
            template = jinja_env.get_template("merge_summary_template.html")
            html_content = template.render(**summary_data)

            return html_content

        except Exception as e:
            logger.error(f"Error rendering summary template: {e}")
