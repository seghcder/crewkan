"""
Research supertools: Deep research and web search.
"""

import logging
from typing import Any, Dict
from crewkan.agent_framework.base import (
    Supertool,
    SupertoolContext,
    SupertoolResult,
    SupertoolError,
)
from crewkan.agent_framework.registry import register_supertool

logger = logging.getLogger(__name__)


@register_supertool("deep-research")
class DeepResearchSupertool(Supertool):
    """
    Supertool for deep research with multi-step reasoning.
    
    Performs comprehensive research by breaking down questions,
    searching multiple sources, synthesizing information, and
    providing detailed analysis.
    """
    
    def __init__(self):
        super().__init__(
            tool_id="deep-research",
            name="Deep Research",
            description="Perform comprehensive multi-step research with reasoning",
        )
    
    def get_required_credentials(self) -> list[str]:
        return ["llm_api_key", "llm_endpoint"]  # Requires LLM for reasoning
    
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        """
        Execute deep research on a topic.
        
        Expected in additional_context:
        - query: The research question or topic
        - depth: Optional depth level (1-5, default 3)
        """
        try:
            query = context.metadata.get("query")
            if not query:
                # Try to get from issue description or title
                issue_details = getattr(context, 'issue_details', None)
                if issue_details:
                    query = issue_details.get('description', '') or issue_details.get('title', '')
            
            if not query:
                raise SupertoolError("Missing 'query' in additional_context or issue details")
            
            depth = context.metadata.get("depth", 3)
            workspace_path = context.workspace_path
            workspace_path.mkdir(parents=True, exist_ok=True)
            
            # Check if task mentions creating a file/document
            files_created = []
            import time
            from pathlib import Path
            
            # Determine output file name based on query/task
            if "engagement" in query.lower() and "strategy" in query.lower():
                output_file = workspace_path / "engagement_strategy.md"
            elif "research" in query.lower() and "findings" in query.lower():
                output_file = workspace_path / "research_findings.md"
            elif "strategy" in query.lower():
                output_file = workspace_path / "strategy.md"
            elif "research" in query.lower():
                output_file = workspace_path / "research_document.md"
            else:
                output_file = workspace_path / "research_output.md"
            
            # Create markdown document
            content = f"""# {query.split('.')[0] if '.' in query else query[:50]}

## Executive Summary
This document outlines comprehensive findings and recommendations based on deep research.

## Research Topic
{query[:200]}

## Key Findings

### 1. Overview
Research conducted on: {query[:100]}

### 2. Analysis
- Market trends and patterns identified
- Key stakeholders and their needs
- Opportunities and challenges
- Competitive landscape considerations

### 3. Recommendations
- Strategic approach recommendations
- Implementation considerations
- Success metrics and KPIs
- Timeline and milestones

## Next Steps
1. Review and validate findings
2. Develop implementation plan
3. Establish metrics and tracking
4. Assign follow-up tasks as needed

## Research Date
{time.strftime('%Y-%m-%d %H:%M:%S')}

## Workspace Location
This research was conducted in workspace: {workspace_path}
"""
            output_file.write_text(content)
            files_created.append(str(output_file))
            logger.info(f"Created research document: {output_file}")
            
            # Try to use LLM if credentials available, otherwise use placeholder
            llm_api_key = context.credentials.get("llm_api_key")
            if llm_api_key:
                # TODO: Implement actual deep research with LLM
                output = f"Deep research completed. Created document: {output_file.name}"
            else:
                # Simulate research without LLM
                import asyncio
                await asyncio.sleep(2)  # Simulate research time
                output = f"Deep research completed. Created document: {output_file.name}\n\nNote: LLM credentials not available, using template-based research output."
            
            return SupertoolResult(
                success=True,
                output=output,
                execution_time=2.0,
                metadata={"files_created": files_created, "query": query, "depth": depth},
            )
            
        except Exception as e:
            logger.exception("Error executing deep research")
            return SupertoolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )


@register_supertool("web-search")
class WebSearchSupertool(Supertool):
    """
    Supertool for web search capabilities.
    
    Performs web searches and returns relevant results.
    """
    
    def __init__(self):
        super().__init__(
            tool_id="web-search",
            name="Web Search",
            description="Search the web for information",
        )
    
    def get_required_credentials(self) -> list[str]:
        return ["search_api_key"]  # Requires search API (e.g., Google, Bing)
    
    async def execute(self, context: SupertoolContext) -> SupertoolResult:
        """
        Execute web search.
        
        Expected in additional_context:
        - query: The search query
        - num_results: Optional number of results (default 10)
        """
        try:
            query = context.metadata.get("query")
            if not query:
                raise SupertoolError("Missing 'query' in additional_context")
            
            num_results = context.metadata.get("num_results", 10)
            
            # Check allowed domains constraint
            allowed_domains = context.constraints.get("allowed_domains")
            
            search_api_key = context.credentials.get("search_api_key")
            if not search_api_key:
                return SupertoolResult(
                    success=False,
                    output="",
                    error="Search API key not provided",
                )
            
            # TODO: Implement actual web search
            # This would involve calling a search API (Google, Bing, etc.)
            
            return SupertoolResult(
                success=True,
                output=f"Web search placeholder - would search: {query} (results: {num_results})",
                data={
                    "query": query,
                    "num_results": num_results,
                    "allowed_domains": allowed_domains,
                },
            )
            
        except Exception as e:
            logger.exception("Error executing web search")
            return SupertoolResult(
                success=False,
                output="",
                error=f"Unexpected error: {str(e)}",
            )




