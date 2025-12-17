import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List
from xml.dom import minidom


class JUnitXMLGenerator:    
    def __init__(self, testsuite_name: str = "BarkoAgent Tests"):
        self.testsuite_name = testsuite_name
    
    def generate_xml(
        self,
        results: List[Dict[str, Any]],
        project_name: str = None,
        batch_report_id: str = None
    ) -> str:
        total_tests = len(results)
        failures = sum(1 for r in results if r.get("failed", False))
        errors = 0
        total_time = sum(r.get("time", 0.0) for r in results)
        
        testsuites = ET.Element("testsuites")
        testsuites.set("name", project_name or self.testsuite_name)
        testsuites.set("tests", str(total_tests))
        testsuites.set("failures", str(failures))
        testsuites.set("errors", str(errors))
        testsuites.set("time", f"{total_time:.3f}")
        
        testsuite_name = project_name or self.testsuite_name
        if batch_report_id:
            testsuite_name = f"{testsuite_name}_{batch_report_id[:8]}"
        
        testsuite = ET.SubElement(testsuites, "testsuite")
        testsuite.set("name", testsuite_name)
        testsuite.set("tests", str(total_tests))
        testsuite.set("failures", str(failures))
        testsuite.set("errors", str(errors))
        testsuite.set("time", f"{total_time:.3f}")
        testsuite.set("timestamp", datetime.utcnow().isoformat())
        
        for result in results:
            testcase = ET.SubElement(testsuite, "testcase")
            testcase.set("name", result.get("name", result.get("id", "unknown")))
            testcase.set("classname", project_name or "BarkoAgent")
            testcase.set("time", f"{result.get('time', 0.0):.3f}")
            
            if result.get("id"):
                testcase.set("id", result["id"])
            
            if result.get("failed", False):
                failure = ET.SubElement(testcase, "failure")
                failure.set("message", "Test failed")
                failure.set("type", "AssertionError")
                
                output = result.get("output", "")
                if output:
                    failure.text = self._sanitize_output(output)
            
            if result.get("output"):
                system_out = ET.SubElement(testcase, "system-out")
                system_out.text = self._sanitize_output(result["output"])
        
        return self._prettify(testsuites)
    
    def _sanitize_output(self, output: str) -> str:
        if not output:
            return ""
        sanitized = "".join(
            char for char in str(output)
            if ord(char) >= 32 or char in "\n\r\t"
        )
        return sanitized
    
    def _prettify(self, elem: ET.Element) -> str:
        rough_string = ET.tostring(elem, encoding="unicode")
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding=None)


def generate_junit_xml(
    results: List[Dict[str, Any]],
    project_name: str = None,
    batch_report_id: str = None,
    testsuite_name: str = "BarkoAgent Tests"
) -> str:
    generator = JUnitXMLGenerator(testsuite_name)
    return generator.generate_xml(results, project_name, batch_report_id)
