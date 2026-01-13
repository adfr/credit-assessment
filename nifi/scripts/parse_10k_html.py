#!/usr/bin/env python3
"""
NiFi ExecuteScript processor for parsing 10-K HTML filings.

This script extracts key sections from SEC 10-K HTML filings:
- Item 1: Business
- Item 1A: Risk Factors
- Item 7: Management's Discussion and Analysis (MD&A)
"""

import re
import html
import json
from org.apache.nifi.processor.io import StreamCallback
from java.io import BufferedReader, InputStreamReader, BufferedWriter, OutputStreamWriter


class ParseTenKCallback(StreamCallback):
    """Callback to parse 10-K HTML and extract key sections."""

    def __init__(self):
        self.max_section_chars = 30000
        self.max_total_chars = 100000

    def process(self, inputStream, outputStream):
        # Read input HTML
        reader = BufferedReader(InputStreamReader(inputStream, "UTF-8"))
        lines = []
        line = reader.readLine()
        while line is not None:
            lines.append(line)
            line = reader.readLine()
        reader.close()

        html_content = "\n".join(lines)

        # Parse and extract
        result = self.extract_sections(html_content)

        # Write output
        writer = BufferedWriter(OutputStreamWriter(outputStream, "UTF-8"))
        writer.write(json.dumps(result))
        writer.close()

    def extract_sections(self, html_content):
        """Extract key sections from 10-K HTML."""
        # Remove script and style tags
        text = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<table[^>]*>.*?</table>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r'<[^>]+>', ' ', text)

        # Decode HTML entities
        text = html.unescape(text)

        # Clean whitespace
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        sections = {}

        # Extract sections
        section_patterns = [
            ("risk_factors", r"(?:ITEM|Item)\s*1A[.\s\-–—]*Risk\s*Factors(.{1000,30000}?)(?:ITEM|Item)\s*\d"),
            ("business", r"(?:ITEM|Item)\s*1[.\s\-–—]*Business(.{1000,30000}?)(?:ITEM|Item)\s*\d"),
            ("mda", r"(?:ITEM|Item)\s*7[.\s\-–—]*Management.{0,50}Discussion(.{1000,30000}?)(?:ITEM|Item)\s*\d"),
        ]

        for section_name, pattern in section_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                content = match.group(1).strip()
                if len(content) > self.max_section_chars:
                    content = content[:self.max_section_chars] + "... [truncated]"
                sections[section_name] = content

        # Combine sections
        combined = ""
        for name, content in sections.items():
            combined += f"\n{'='*60}\n{name.upper().replace('_', ' ')}\n{'='*60}\n{content}\n"

        if not combined:
            # Fallback: extract long paragraphs
            paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 150]
            combined = '\n\n'.join(paragraphs[:50])

        if len(combined) > self.max_total_chars:
            combined = combined[:self.max_total_chars]

        return {
            "content": combined,
            "sections_found": list(sections.keys()),
            "content_length": len(combined)
        }


# NiFi script execution
flowFile = session.get()
if flowFile is not None:
    flowFile = session.write(flowFile, ParseTenKCallback())

    # Update attributes with extraction metadata
    flowFile = session.putAttribute(flowFile, "parsing_status", "success")

    session.transfer(flowFile, REL_SUCCESS)
